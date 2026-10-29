from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.categories.consumable_migration import (
    MigrationBlocked,
    MigrationInputError,
    apply_migration,
    build_snapshot,
    read_code_file,
    write_workbook,
)
from apps.categories.models import ConsumableMigrationRun


class Command(BaseCommand):
    help = '按 Excel 编号清单预演或迁移消耗品，结清在用和回收库余额并生成影响工作簿（默认只读）'

    def add_arguments(self, parser):
        parser.add_argument('--input', help='首列标题为“资产编号”的 Excel 清单（预演/执行必填）')
        parser.add_argument('--output', help='影响工作簿输出路径；默认与输入文件同目录')
        parser.add_argument('--apply', action='store_true', help='提交在用和回收库结清调整及管理方式迁移')
        parser.add_argument('--expected-sha256', help='执行时必须匹配已审阅预演工作簿中的输入摘要')
        parser.add_argument('--force', action='store_true', help='显式覆盖已存在的输出文件')
        parser.add_argument('--run-id', help='只读重导已执行的迁移工作簿，不重复写入业务数据')

        parser.add_argument(
            '--ignore-inventory-locks', action='store_true',
            help='Explicitly ignore active inventory tasks for this migration while retaining branch barriers.',
        )

    def handle(self, *args, **options):
        if options['run_id']:
            if options['ignore_inventory_locks']:
                raise CommandError('--run-id cannot be combined with --ignore-inventory-locks')
            return self._export_existing_run(options)
        if options['expected_sha256'] and not options['apply']:
            raise CommandError('--expected-sha256 仅适用于 --apply')
        if not options['input']:
            raise CommandError('预演或执行时必须提供 --input Excel 文件')

        input_path = Path(options['input']).expanduser().resolve()
        if not input_path.is_file():
            raise CommandError(f'输入文件不存在：{input_path}')
        output_path = self._output_path(input_path, options['output'])
        if input_path == output_path:
            raise CommandError('输出路径不能覆盖输入清单')
        if output_path.suffix.lower() != '.xlsx':
            raise CommandError('输出文件扩展名必须为 .xlsx')
        self._ensure_output_available(output_path, options['force'])
        try:
            codes, input_issues = read_code_file(input_path)
        except MigrationInputError as exc:
            raise CommandError(str(exc)) from exc
        source_sha256 = hashlib.sha256(input_path.read_bytes()).hexdigest()

        if options['apply']:
            expected_sha256 = (options['expected_sha256'] or '').strip().lower()
            if len(expected_sha256) != 64 or any(
                character not in '0123456789abcdef' for character in expected_sha256
            ):
                raise CommandError('--apply 必须提供已审阅预演工作簿中的 64 位 --expected-sha256')
            if source_sha256 != expected_sha256:
                raise CommandError('输入文件 SHA-256 与已审阅预演不一致；未执行迁移')
            try:
                run = apply_migration(
                    codes,
                    input_issues,
                    input_path,
                    source_sha256,
                    ignore_inventory_locks=options['ignore_inventory_locks'],
                )
            except MigrationBlocked as exc:
                snapshot = exc.snapshot
                snapshot.update({
                    'source_filename': input_path.name,
                    'source_sha256': source_sha256,
                })
                self._save_report(snapshot, output_path, options['force'])
                raise CommandError(
                    '预检未通过；整批未写入。阻断原因已输出到工作簿：'
                    + '；'.join(snapshot['blockers'])
                ) from exc
            except RuntimeError as exc:
                raise CommandError(str(exc)) from exc

            snapshot = run.snapshot
            try:
                self._save_report(snapshot, output_path, options['force'])
            except Exception as exc:
                raise CommandError(
                    f'数据库事务已经提交，但工作簿生成失败：{exc}；'
                    f'可用 --run-id {run.pk} 重导，不会重复调整台账。'
                ) from exc
            run.status = ConsumableMigrationRun.STATUS_REPORTED
            run.report_path = str(output_path)
            run.save(update_fields=['status', 'report_path', 'updated_at'])
            self.stdout.write(self.style.SUCCESS(
                f'迁移已提交：{run.pk}；工作簿：{output_path}'
            ))
            return

        snapshot = build_snapshot(
            codes,
            input_issues=input_issues,
            mode='DRY_RUN',
            ignore_inventory_locks=options['ignore_inventory_locks'],
        )
        snapshot.update({
            'source_filename': input_path.name,
            'source_sha256': source_sha256,
        })
        self._save_report(snapshot, output_path, options['force'])
        if snapshot['blockers']:
            raise CommandError(
                '预演发现阻断，未写入任何数据；详情见工作簿：'
                + '；'.join(snapshot['blockers'])
            )
        self.stdout.write(self.style.SUCCESS(
            f'只读预演完成：{snapshot["target_count"]} 个编号、'
            f'{snapshot["branch_count"]} 个相关分公司；未写入数据。工作簿：{output_path}'
        ))

    @staticmethod
    def _output_path(input_path, output_value):
        if output_value:
            return Path(output_value).expanduser().resolve()
        return input_path.with_name(f'{input_path.stem}_消耗品迁移影响.xlsx')

    @staticmethod
    def _ensure_output_available(output_path, force):
        if output_path.exists() and not force:
            raise CommandError(f'输出文件已存在，为避免覆盖请更换路径或传入 --force：{output_path}')

    def _save_report(self, snapshot, output_path, force):
        self._ensure_output_available(output_path, force)
        try:
            path = write_workbook(snapshot, output_path, force=force)
        except Exception as exc:
            raise CommandError(f'工作簿生成失败：{exc}') from exc
        return path

    def _export_existing_run(self, options):
        if options['input'] or options['apply'] or options['expected_sha256']:
            raise CommandError('--run-id 重导模式不能同时使用 --input、--apply 或 --expected-sha256')
        try:
            run_id = uuid.UUID(options['run_id'])
        except (ValueError, TypeError, AttributeError) as exc:
            raise CommandError('--run-id 必须是有效 UUID') from exc
        try:
            run = ConsumableMigrationRun.objects.get(pk=run_id)
        except ConsumableMigrationRun.DoesNotExist as exc:
            raise CommandError(f'找不到迁移运行记录：{run_id}') from exc
        if not run.snapshot:
            raise CommandError(f'迁移运行记录 {run_id} 没有可导出的快照')
        output_path = Path(options['output']).expanduser().resolve() if options['output'] else None
        if output_path is None:
            raise CommandError('--run-id 重导时必须提供 --output')
        if output_path.suffix.lower() != '.xlsx':
            raise CommandError('输出文件扩展名必须为 .xlsx')
        self._ensure_output_available(output_path, options['force'])
        snapshot = dict(run.snapshot)
        snapshot['mode'] = 'APPLIED'
        snapshot['status'] = '已执行结果重导'
        self._save_report(snapshot, output_path, options['force'])
        run.status = ConsumableMigrationRun.STATUS_REPORTED
        run.report_path = str(output_path)
        run.save(update_fields=['status', 'report_path', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(
            f'已从持久化快照重导迁移运行 {run_id}；没有重复修改业务数据。工作簿：{output_path}'
        ))
