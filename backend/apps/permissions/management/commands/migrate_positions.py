"""岗位换岗迁移：supervisor 退役 → 岗位模板化（逐人 diff，只补不删）。

默认 dry-run 输出逐人清单：
  岗位 old→new ｜ 模板操作码补授 ｜ 任命节点 ｜ 生效范围
--apply 执行：
  1. 存量 supervisor 按 LEGACY_POSITION_MAP 换岗（默认 → manager）；
  2. 按岗位模板补建缺失的 OperationGrant（绝不删除既有授权）；
  3. ManagementScope 一律保留（降级为「额外授权」）。
"""
from django.core.management.base import BaseCommand

from apps.permissions.models import OperationGrant
from apps.permissions.positions import LEGACY_POSITION_MAP, template_operations
from apps.permissions.scope import resolve_user_scope


class Command(BaseCommand):
    help = '岗位换岗迁移：supervisor 退役 + 按岗位模板补授操作码（默认 dry-run，--apply 执行；只补不删）'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        from apps.users.models import User

        users = User.objects.exclude(role='admin').filter(status='active').order_by('name')
        changed_roles, granted_ops, kept = 0, 0, 0

        for user in users:
            old_role = user.role
            new_role = LEGACY_POSITION_MAP.get(old_role, old_role)
            role_changed = new_role != old_role

            tpl_ops = template_operations(new_role)
            existing = set(OperationGrant.objects.filter(user=user).values_list('code', flat=True))
            to_grant = [c for c in tpl_ops if c not in existing]

            scope = resolve_user_scope(user)
            appointments = (
                len(scope.appointed_regions) + len(scope.appointed_teams) + len(scope.appointed_branches)
            )
            scope_desc = '全部' if scope.all else f'{len(scope.branches)} 个分公司'

            role_part = f'岗位 {old_role}→{new_role}' if role_changed else f'岗位 {old_role}'
            grant_part = f'补授 {",".join(to_grant)}' if to_grant else '无补授'
            appoint_part = f'{appointments} 项任命' if appointments else '无任命'
            self.stdout.write(
                f'  {user.name}（{user.phone}）：{role_part} ｜ {grant_part} ｜ {appoint_part} ｜ 范围 {scope_desc}'
            )

            if apply:
                if role_changed:
                    user.role = new_role
                    user.save(update_fields=['role'])
                    changed_roles += 1
                if to_grant:
                    OperationGrant.objects.bulk_create(
                        [OperationGrant(user=user, code=c) for c in to_grant],
                        ignore_conflicts=True,
                    )
                    granted_ops += len(to_grant)
            elif role_changed:
                changed_roles += 1
            elif to_grant:
                granted_ops += len(to_grant)
            else:
                kept += 1

        summary = (
            f'换岗 {changed_roles} 人、补授 {granted_ops} 项操作码、无变化 {kept} 人'
            + ('（已写入）' if apply else '（dry-run，未写库；确认后加 --apply 执行）')
        )
        self.stdout.write(self.style.SUCCESS(summary))
