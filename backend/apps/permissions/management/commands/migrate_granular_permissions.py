"""Preview and safely apply/restore the granular permission migration."""
import json
from pathlib import Path
from uuid import UUID

from django.core.management import BaseCommand, CommandError
from django.db import transaction

from apps.audit.models import AuditLog
from apps.permissions.granular_migration import (
    PLAN_SCHEMA,
    SNAPSHOT_SCHEMA,
    _authorization_rows,
    authorization_digest,
    build_migration_plan,
    expected_authorization_digest,
    _appointment_scope_row,
    restore_authorization,
    seal_snapshot,
    snapshot_payload,
    validate_snapshot,
)
from apps.permissions.models import OperationGrant
from apps.users.models import User


def _read_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except OSError as exc:
        raise CommandError(f'无法读取{label}文件 {path}: {exc}') from exc
    except json.JSONDecodeError as exc:
        raise CommandError(f'{label}不是有效 JSON: {exc}') from exc


def _write_json_new(path, data, label):
    target = Path(path)
    if target.exists():
        raise CommandError(f'{label}文件已存在，不覆盖：{target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
    except FileExistsError as exc:
        raise CommandError(f'{label}文件已存在，不覆盖：{target}') from exc
    except OSError as exc:
        raise CommandError(f'无法写入{label}文件 {target}: {exc}') from exc
    return target


class Command(BaseCommand):
    help = '预览或迁移旧账号级权限；默认只读预览，支持快照核验和恢复。'

    def add_arguments(self, parser):
        action = parser.add_mutually_exclusive_group()
        action.add_argument('--apply', action='store_true', help='应用已生成的预览计划')
        action.add_argument('--verify-snapshot', metavar='PATH', help='核验快照对应的授权状态')
        action.add_argument('--restore-snapshot', metavar='PATH', help='从快照恢复授权状态')
        parser.add_argument('--output', help='预览计划 JSON 输出路径；缺省写到标准输出')
        parser.add_argument(
            '--snapshot-output',
            help='只读导出当前权限与数据范围发布前快照；需同时提供 --output，避免将逐账号信息写到标准输出',
        )
        parser.add_argument('--plan', help='--apply 使用的预览计划文件')
        parser.add_argument('--confirm', help='--apply 必须填写预览显示的 plan_id')
        parser.add_argument('--actor-id', help='应用或恢复时执行操作的系统管理员账号 ID')
        parser.add_argument('--snapshot', help='--apply 必须填写一个尚不存在的快照文件路径')
        parser.add_argument(
            '--accept-unmapped', action='store_true',
            help='确认继续迁移已映射权限，并保留计划中列出的未映射旧权限码供人工处理',
        )
        parser.add_argument(
            '--preserve-scope-id', action='append', default=[], metavar='ID',
            help='逐条确认保留预览列出的来源不明数据范围记录；可重复指定',
        )
        parser.add_argument(
            '--drop-scope-id', action='append', default=[], metavar='ID',
            help='逐条确认删除预览列出的来源不明数据范围记录；可重复指定',
        )
        parser.add_argument('--confirm-restore', help='--restore-snapshot 必须填写快照显示的 snapshot_id')

    def handle(self, *args, **options):
        if options['verify_snapshot']:
            self._verify_snapshot(options['verify_snapshot'])
            return
        if options['restore_snapshot']:
            actor = self._require_admin_actor(options['actor_id'])
            self._restore_snapshot(options['restore_snapshot'], options['confirm_restore'], actor)
            return
        if options['apply']:
            actor = self._require_admin_actor(options['actor_id'])
            self._apply(options, actor)
            return
        if options['snapshot_output'] and not options['output']:
            raise CommandError('--snapshot-output 必须同时提供 --output，预览中包含员工信息，不能输出到标准输出')
        if (options['plan'] or options['confirm'] or options['snapshot']
                or options['accept_unmapped']
                or options['preserve_scope_id'] or options['drop_scope_id']
                or options['actor_id']):
            raise CommandError('apply 专用参数只能与 --apply 一起使用')
        self._preview(options['output'], options['snapshot_output'])

    @staticmethod
    def _require_admin_actor(actor_id):
        if not actor_id:
            raise CommandError('--apply 和 --restore-snapshot 必须提供 --actor-id <系统管理员账号 ID>，以记录审计操作人')
        try:
            actor_id = UUID(str(actor_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise CommandError('--actor-id 必须对应现有系统管理员账号') from exc
        actor = User.objects.filter(pk=actor_id).first()
        if actor is None or actor.role != 'admin':
            raise CommandError('--actor-id 必须对应现有系统管理员账号')
        return actor

    @staticmethod
    def _user_authorization_state(user_id):
        grants = sorted(OperationGrant.objects.filter(user_id=user_id).values_list('code', flat=True))
        from apps.permissions.models import ManagementScope
        scopes = list(ManagementScope.objects.filter(user_id=user_id).order_by('id').values(
            'id', 'is_all_data', 'region_id', 'branch_id', 'team_id',
        ))
        return {
            'operations': grants,
            'scopes': [{key: str(value) if value is not None and key != 'is_all_data' else value
                        for key, value in scope.items()} for scope in scopes],
        }

    @staticmethod
    def _write_audit(actor, target, before, after, description):
        AuditLog.objects.create(
            user=actor,
            user_name=actor.name,
            user_phone=actor.phone,
            action='update',
            resource_type='user_authorization',
            resource_id=target.id,
            resource_name=target.name,
            description=description,
            before_data=before,
            after_data=after,
            request_path='migrate_granular_permissions',
            request_method='COMMAND',
        )

    def _preview(self, output_path, snapshot_output_path=None):
        plan = build_migration_plan()
        if output_path:
            target = _write_json_new(output_path, plan, '预览计划')
            snapshot_target = None
            snapshot = None
            if snapshot_output_path:
                snapshot = snapshot_payload(plan)
                snapshot['kind'] = 'pre_release_authorization'
                snapshot = seal_snapshot(snapshot)
                snapshot_target = _write_json_new(snapshot_output_path, snapshot, '发布前快照')
            self.stdout.write(self.style.SUCCESS(
                f"只读预览已写入 {target}；plan_id={plan['plan_id']}；"
                f"账号 {plan['summary']['account_count']}，待人工复核 "
                f"{plan['summary']['pending_review_grant_count']} 项旧授权 "
                f"（部分映射 {plan['summary']['partially_mapped_grant_count']} 项）。"
                + (
                    f"发布前授权快照已写入 {snapshot_target}；snapshot_id={snapshot['snapshot_id']}。"
                    if snapshot else ''
                )
            ))
            return
        self.stdout.write(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))

    def _apply(self, options, actor):
        plan_path = options['plan']
        confirmation = options['confirm']
        snapshot_path = options['snapshot']
        if not plan_path or not confirmation or not snapshot_path:
            raise CommandError('--apply 必须同时提供 --plan、--confirm <plan_id> 和 --snapshot <新文件路径>')

        supplied = _read_json(plan_path, '预览计划')
        if supplied.get('schema') != PLAN_SCHEMA:
            raise CommandError('预览计划版本不兼容或文件不是权限迁移计划')
        if confirmation != supplied.get('plan_id'):
            raise CommandError('确认值与预览计划 plan_id 不匹配')

        current = build_migration_plan()
        if current['source_digest'] != supplied.get('source_digest'):
            raise CommandError('授权或组织数据在预览后发生变化，请重新生成预览计划')
        if current['plan_id'] != supplied.get('plan_id'):
            raise CommandError('预览计划已过期或映射版本已变化，请重新生成计划')
        expected_plan = dict(current)
        supplied_plan = dict(supplied)
        expected_plan.pop('generated_at', None)
        supplied_plan.pop('generated_at', None)
        if supplied_plan != expected_plan:
            raise CommandError('预览计划内容与当前审核映射不一致，请勿编辑计划后应用')
        pending_reviews = current['unmapped_grants'] + current['partially_mapped_grants']
        if pending_reviews and not options['accept_unmapped']:
            raise CommandError(
                f"计划含 {len(pending_reviews)} 项待人工复核的旧授权，"
                f"其中部分映射 {len(current['partially_mapped_grants'])} 项；"
                '复核后如接受保留未确认的旧权限码，请显式传入 --accept-unmapped'
            )
        preserve_scope_ids, drop_scope_ids = self._scope_decisions(current, options)

        snapshot = snapshot_payload(current)
        snapshot['expected_after_authorization_digest'] = expected_authorization_digest(
            snapshot, current, drop_scope_ids,
        )
        snapshot = seal_snapshot(snapshot)
        _write_json_new(snapshot_path, snapshot, '迁移快照')

        mapped_by_user = {}
        admin_user_ids = {
            account['user_id']
            for account in current['accounts']
            if account['automatic_admin_all']
        }
        for account in current['accounts']:
            if account['automatic_admin_all']:
                continue
            for mapping in account['grant_mappings']:
                if mapping['state'] in ('mapped', 'partially_mapped'):
                    entry = mapped_by_user.setdefault(account['user_id'], {'sources': set(), 'targets': set()})
                    if mapping['state'] == 'mapped':
                        entry['sources'].add(mapping['from'])
                    entry['targets'].update(mapping['to'])
        appointment_scopes_by_user = {
            account['user_id']: account['scope']['appointment_scopes_to_preserve']
            for account in current['accounts']
            if account['scope']['appointment_scopes_to_preserve']
        }

        with transaction.atomic():
            if build_migration_plan()['source_digest'] != current['source_digest']:
                raise CommandError('授权数据在应用事务开始时发生变化，请重新生成预览计划')
            changed_user_ids = set(mapped_by_user) | admin_user_ids | set(appointment_scopes_by_user)
            if drop_scope_ids:
                from apps.permissions.models import ManagementScope
                changed_user_ids.update(str(user_id) for user_id in ManagementScope.objects.filter(
                    pk__in=drop_scope_ids,
                ).values_list('user_id', flat=True))
            before_by_user = {
                user_id: self._user_authorization_state(user_id)
                for user_id in changed_user_ids
            }
            if admin_user_ids:
                OperationGrant.objects.filter(user_id__in=admin_user_ids).delete()
                from apps.permissions.models import ManagementScope
                ManagementScope.objects.filter(user_id__in=admin_user_ids).delete()
            for user_id, mapping in mapped_by_user.items():
                current_codes = set(OperationGrant.objects.filter(user_id=user_id).values_list('code', flat=True))
                resulting_codes = (current_codes - mapping['sources']) | mapping['targets']
                OperationGrant.objects.filter(
                    user_id=user_id, code__in=mapping['sources'],
                ).delete()
                existing = set(OperationGrant.objects.filter(user_id=user_id).values_list('code', flat=True))
                OperationGrant.objects.bulk_create([
                    OperationGrant(user_id=user_id, code=code)
                    for code in sorted(resulting_codes - existing)
                ])
            if drop_scope_ids:
                from apps.permissions.models import ManagementScope
                ManagementScope.objects.filter(pk__in=drop_scope_ids).delete()
            from apps.permissions.models import ManagementScope
            for user_id, appointments in appointment_scopes_by_user.items():
                for appointment in appointments:
                    scope = _appointment_scope_row(user_id, appointment)
                    ManagementScope.objects.get_or_create(
                        user_id=user_id,
                        is_all_data=scope['is_all_data'],
                        region_id=scope['region_id'],
                        team_id=scope['team_id'],
                        branch_id=scope['branch_id'],
                    )
            actual_digest = authorization_digest()
            if actual_digest != snapshot['expected_after_authorization_digest']:
                raise CommandError('应用结果与预览计划不一致，事务已回滚；快照文件保留供检查')
            for user_id, before in before_by_user.items():
                target = User.objects.get(pk=user_id)
                after = self._user_authorization_state(user_id)
                if before != after:
                    self._write_audit(
                        actor, target, before, after,
                        f'旧权限目录迁移已应用；plan_id={current["plan_id"]}；原因：已确认的权限目录迁移',
                    )

        self.stdout.write(self.style.SUCCESS(
            f"权限迁移已应用。快照：{snapshot_path}；snapshot_id={snapshot['snapshot_id']}；"
            f"迁移计划：{current['plan_id']}；待人工复核旧码保留 {len(pending_reviews)} 项 "
            f"（部分映射 {len(current['partially_mapped_grants'])} 项）；"
            f'数据范围逐条选择：保留 {len(preserve_scope_ids)} 项、删除 {len(drop_scope_ids)} 项。'
        ))

    @staticmethod
    def _scope_decisions(plan, options):
        records = [
            record
            for account in plan['accounts']
            for record in account['scope']['unclassified_records']
        ]
        expected = {record['scope_id'] for record in records}
        preserve = options['preserve_scope_id']
        drop = options['drop_scope_id']

        if len(preserve) != len(set(preserve)) or len(drop) != len(set(drop)):
            raise CommandError('同一 scope ID 不能重复指定保留或删除。')
        if set(preserve) & set(drop):
            raise CommandError('同一 scope ID 不能同时选择保留和删除。')
        supplied = set(preserve) | set(drop)
        unknown = supplied - expected
        if unknown:
            raise CommandError(f'预览中不存在这些 scope ID：{", ".join(sorted(unknown))}')
        missing = expected - supplied
        if missing:
            raise CommandError(
                f'仍有 {len(missing)} 条来源不明的数据范围未逐条选择；'
                '请对每个预览中的 ID 指定 --preserve-scope-id 或 --drop-scope-id。'
            )
        return set(preserve), set(drop)

    def _verify_snapshot(self, path):
        snapshot = _read_json(path, '迁移快照')
        self._validate_snapshot(snapshot)
        actual = authorization_digest()
        if actual == snapshot.get('expected_after_authorization_digest'):
            self.stdout.write(self.style.SUCCESS(
                f"快照 {snapshot['snapshot_id']} 核验通过：当前授权与迁移后状态一致。"
            ))
            return
        if actual == snapshot.get('before_authorization_digest'):
            self.stdout.write(self.style.WARNING(
                f"快照 {snapshot['snapshot_id']} 核验通过：迁移尚未应用，当前授权仍与迁移前一致。"
            ))
            return
        raise CommandError('当前授权既不匹配迁移前也不匹配迁移后快照；可能存在后续授权变更，拒绝自动判定。')

    def _restore_snapshot(self, path, confirmation, actor):
        snapshot = _read_json(path, '迁移快照')
        self._validate_snapshot(snapshot)
        if not confirmation or confirmation != snapshot.get('snapshot_id'):
            raise CommandError('恢复必须提供与快照一致的 --confirm-restore <snapshot_id>')

        actual = authorization_digest()
        if actual == snapshot.get('before_authorization_digest'):
            self.stdout.write(self.style.WARNING('当前授权已经处于快照原始状态，无需恢复。'))
            return
        if actual != snapshot.get('expected_after_authorization_digest'):
            raise CommandError('迁移后授权已发生变化，拒绝覆盖；请先人工复核当前授权。')

        with transaction.atomic():
            if authorization_digest() != snapshot['expected_after_authorization_digest']:
                raise CommandError('恢复前授权状态发生变化，事务已取消。')
            current_authorization = _authorization_rows()
            changed_user_ids = {
                str(row['user_id'])
                for row in snapshot['authorization']['grants'] + snapshot['authorization']['scopes']
            }
            changed_user_ids.update(
                str(row['user_id'])
                for row in current_authorization['grants'] + current_authorization['scopes']
            )
            before_by_user = {
                user_id: self._user_authorization_state(user_id)
                for user_id in changed_user_ids
            }
            restore_authorization(snapshot)
            if authorization_digest() != snapshot['before_authorization_digest']:
                raise CommandError('恢复结果校验失败，事务已回滚。')
            for user_id, before in before_by_user.items():
                target = User.objects.get(pk=user_id)
                after = self._user_authorization_state(user_id)
                if before != after:
                    self._write_audit(
                        actor, target, before, after,
                        f'旧权限目录迁移已从快照恢复；snapshot_id={snapshot["snapshot_id"]}；原因：恢复已确认的权限目录迁移',
                    )
        self.stdout.write(self.style.SUCCESS(
            f"已从快照恢复权限和数据范围：{path}（{snapshot['snapshot_id']}）。"
        ))

    @staticmethod
    def _validate_snapshot(snapshot):
        if snapshot.get('schema') != SNAPSHOT_SCHEMA:
            raise CommandError('快照版本不兼容或文件不是权限迁移快照')
        if not validate_snapshot(snapshot):
            raise CommandError('快照摘要校验失败，文件可能不完整或已被修改')
        if snapshot.get('expected_after_authorization_digest') is None:
            raise CommandError('发布前快照仅用于迁移前差异复核；迁移应用后会另行生成可核验和恢复的快照')
