"""Normalize retired position labels and clear authorization on position changes."""
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.audit.models import AuditLog
from apps.permissions.models import ManagementScope, OperationGrant
from apps.permissions.legacy_position_map import LEGACY_POSITION_MAP
from apps.users.models import User


class Command(BaseCommand):
    help = '迁移退役岗位标记；应用时清除旧权限和自定义数据范围并记录审计（默认 dry-run）'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行岗位标记更新（默认仅预览）')
        parser.add_argument('--actor-id', help='应用时执行操作的系统管理员账号 ID')

    def handle(self, *args, **options):
        apply = options['apply']
        actor_id = options['actor_id']
        if apply:
            if not actor_id:
                raise CommandError('--apply 必须提供 --actor-id <系统管理员账号 ID>，以记录授权重置审计')
            try:
                actor_id = UUID(str(actor_id))
            except (TypeError, ValueError, AttributeError) as exc:
                raise CommandError('--actor-id 必须对应现有系统管理员账号') from exc
            actor = User.objects.filter(pk=actor_id).first()
            if actor is None or actor.role != 'admin':
                raise CommandError('--actor-id 必须对应现有系统管理员账号')
        elif actor_id:
            raise CommandError('--actor-id 只能与 --apply 一起使用')
        changed = 0

        users = User.objects.filter(
            role__in=LEGACY_POSITION_MAP,
            status='active',
        ).order_by('name')

        for user in users:
            new_role = LEGACY_POSITION_MAP[user.role]
            self.stdout.write(
                f'  {user.name}（{user.phone}）：岗位标记 {user.role} → {new_role}；'
                '应用时清除原操作权限和自定义数据范围'
            )
            changed += 1
            if apply:
                with transaction.atomic():
                    user = User.objects.select_for_update().get(pk=user.pk)
                    before = {
                        'role': user.role,
                        'operations': sorted(user.operation_grants.values_list('code', flat=True)),
                        'scopes': [
                            {
                                key: str(value) if value is not None and key != 'is_all_data' else value
                                for key, value in scope.items()
                            }
                            for scope in user.management_scopes.order_by('id').values(
                                'id', 'is_all_data', 'region_id', 'branch_id', 'team_id',
                            )
                        ],
                    }
                    user.role = new_role
                    user.save(update_fields=['role'])
                    user.operation_grants.all().delete()
                    user.management_scopes.all().delete()
                    user._mgmt_scope_cache = None
                    AuditLog.objects.create(
                        user=actor,
                        user_name=actor.name,
                        user_phone=actor.phone,
                        action='update',
                        resource_type='user_authorization',
                        resource_id=user.id,
                        resource_name=user.name,
                        description='退役岗位规范化，已清除原业务权限和自定义数据范围；原因：员工岗位变更',
                        before_data=before,
                        after_data={
                            'role': user.role,
                            'operations': [],
                            'scopes': [],
                        },
                        request_path='migrate_positions',
                        request_method='COMMAND',
                    )

        mode = '已写入' if apply else 'dry-run，未写库；确认后加 --apply --actor-id <管理员账号 ID> 执行'
        self.stdout.write(self.style.SUCCESS(
            f'更新退役岗位标记 {changed} 人；应用时清理原授权并记录审计（{mode}）'
        ))
