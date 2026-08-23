"""存量迁移执行：Asset 聚合分桶 → 期初调整单 → 台账入账 + 部门归一。

前置：
  - preview_ledger_migration 无阻断（未登记编号 / 无分公司行）
  - 全量备份完成（--confirm-backup 显式声明）

幂等：重复执行前会拒绝（已存在期初单时需 --reset 先清空台账与期初单）。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import AssetStock, LedgerAdjustment
from apps.assets.services import ledger as ledger_service
from apps.organizations.models import Branch, Department
from apps.assets.management.commands.preview_ledger_migration import (
    collect_aggregates, collect_departments,
)


class Command(BaseCommand):
    help = '台账存量迁移：Asset 聚合 → 期初调整单 → service 入账 + 部门字典归一'

    def add_arguments(self, parser):
        parser.add_argument('--confirm-backup', action='store_true',
                            help='声明已完成全量备份（必需）')
        parser.add_argument('--reset', action='store_true',
                            help='先清空台账行与期初单（重复执行时用）')
        parser.add_argument('--skip-departments', action='store_true',
                            help='跳过部门归一（仅迁移台账）')

    def handle(self, *args, **options):
        if not options['confirm_backup']:
            raise CommandError('请先完成全量备份并以 --confirm-backup 声明')

        if LedgerAdjustment.objects.filter(is_initial=True).exists() and not options['reset']:
            raise CommandError('已存在期初单；如需重跑请加 --reset（将清空台账行与期初单）')

        buckets, unregistered, no_branch, branch_map = collect_aggregates()
        if unregistered:
            raise CommandError(
                f'存在 {len(unregistered)} 个未登记编号（preview_ledger_migration 可见清单），'
                '请先补录品目字典或修正资产明细'
            )
        if no_branch:
            raise CommandError(
                f'存在 {len(no_branch)} 行无法定位分公司的存量数据，请先修正（preview 可见清单）'
            )

        with transaction.atomic():
            if options['reset']:
                AssetStock.objects.all().delete()
                LedgerAdjustment.objects.filter(is_initial=True).delete()
                self.stdout.write('已清空台账行与期初单（重跑模式）')

            created = 0
            for (branch_id, code), bucket in sorted(buckets.items()):
                branch = branch_map[branch_id]
                item = _get_item(code)
                for column, qty in (
                    (ledger_service.COLUMN_STOCK, bucket['在库数量']),
                    (ledger_service.COLUMN_IN_USE, bucket['在用数量']),
                ):
                    if qty:
                        ledger_service.apply_adjustment(
                            branch, item, column, qty,
                            reason='系统期初', is_initial=True,
                        )
                        created += 1
            self.stdout.write(self.style.SUCCESS(
                f'期初入账完成：{len(buckets)} 个维度行，{created} 条期初调整单'
            ))

            if not options['skip_departments']:
                dept_map, anomalies = collect_departments()
                made = 0
                branch_by_name = {b.name: b for b in Branch.objects.all()}
                for branch_name, depts in dept_map.items():
                    branch = branch_by_name.get(branch_name)
                    if branch is None:
                        continue
                    for dept in depts:
                        _, created_flag = Department.objects.get_or_create(branch=branch, name=dept)
                        made += 1 if created_flag else 0
                self.stdout.write(self.style.SUCCESS(
                    f'部门归一完成：新增 {made} 条字典行'
                    + (f'（{len(anomalies)} 行分公司为空的异常文本已跳过，需人工处理）' if anomalies else '')
                ))

        from django.core.management import call_command
        call_command('check_ledger_consistency')
        self.stdout.write(self.style.SUCCESS('迁移后对账通过（零差异）'))


def _get_item(code):
    from apps.categories.models import Category
    try:
        return Category.objects.get(asset_code=code)
    except Category.DoesNotExist:
        raise CommandError(f'品目 {code} 未登记（不应到达此处，preview 已阻断）')
