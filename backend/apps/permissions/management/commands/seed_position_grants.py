"""批量种子岗位授权：操作码按岗位模板补齐 + manager/leader 补本分公司节点 + 清 admin 冗余授权。

背景（2026-09-08 批量建号只建了账号/组织/负责人任命，未建授权记录）：
  - 运行时操作鉴权只看 OperationGrant 表 → 未补码的 director/manager 无任何业务操作
  - 分公司行政（manager）无任命也无节点授权 → 管理数据范围为空
  - admin 走职位兜底，持授权记录属冗余（check_seed_grants 判 FAIL）

口径（口诀：岗位定操作、任命定范围、特例才单独授予）：
  1. 非 admin 在职用户按岗位模板补齐操作码（只补不删，特例授权保留）
  2. manager/leader 挂有本分公司的，补该分公司节点授权（幂等）
  3. director 范围来自大区负责人任命（任命即授权），不重复建节点记录
  4. 清空 admin 的授权记录（运行时恒真，删除零损失）
  5. 范围仍为空者（无 branch 无任命，如轮空人员）列人工清单，不猜节点

默认 dry-run 逐人打印计划；--apply 写入。幂等可重复执行。
"""
from django.core.management.base import BaseCommand

from apps.permissions.models import ManagementScope, OperationGrant
from apps.permissions.positions import template_operations
from apps.permissions.scope import resolve_user_scope
from apps.users.models import User


class Command(BaseCommand):
    help = ('批量种子岗位授权（操作码按岗位模板补齐 + manager/leader 补本分公司节点 + '
            '清 admin 冗余授权；默认 dry-run，--apply 执行；只补不删）')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']

        admin_scope_n = ManagementScope.objects.filter(user__role='admin').count()
        admin_grant_n = OperationGrant.objects.filter(user__role='admin').count()
        if admin_scope_n or admin_grant_n:
            self.stdout.write(
                f'admin 冗余授权待清理: {admin_scope_n} 节点 + {admin_grant_n} 操作码（admin 走职位兜底，删除零损失）'
            )

        stats = {'ops': 0, 'scopes': 0, 'unchanged': 0}
        manual = []

        users = User.objects.exclude(role='admin').filter(status='active').order_by('name')
        for user in users:
            existing_ops = set(OperationGrant.objects.filter(user=user).values_list('code', flat=True))
            to_grant = [c for c in template_operations(user.role) if c not in existing_ops]

            # 全部数据授权已覆盖一切节点，无需再补
            has_all_data = user.management_scopes.filter(is_all_data=True).exists()
            add_branch_scope = (
                user.role in ('manager', 'leader') and user.branch_id and not has_all_data
                and not ManagementScope.objects.filter(user=user, branch_id=user.branch_id).exists()
            )

            scope = resolve_user_scope(user)  # 授权记录 ∪ 树负责人任命
            parts = [f'岗位 {user.role}', f'补授 {",".join(to_grant)}' if to_grant else '无补授']
            if add_branch_scope:
                parts.append(f'范围 +{user.branch.name}')
            elif not scope.is_empty:
                parts.append('范围来自任命' if not user.management_scopes.exists() else '范围已有')
            else:
                hint = '（supervisor/staff 先跑 migrate_positions 换岗）' if user.role in ('supervisor', 'staff') else ''
                parts.append(f'⚠范围待人工{hint}')
                manual.append(user)

            self.stdout.write(f'  {user.name}（{user.phone}）：{" ｜ ".join(parts)}')

            stats['ops'] += len(to_grant)
            if add_branch_scope:
                stats['scopes'] += 1
            if apply:
                if to_grant:
                    OperationGrant.objects.bulk_create(
                        [OperationGrant(user=user, code=c) for c in to_grant],
                        ignore_conflicts=True,
                    )
                if add_branch_scope:
                    ManagementScope.objects.create(user=user, branch_id=user.branch_id)
            if not to_grant and not add_branch_scope and not scope.is_empty:
                stats['unchanged'] += 1

        if apply:
            deleted_scope, _ = ManagementScope.objects.filter(user__role='admin').delete()
            deleted_grant, _ = OperationGrant.objects.filter(user__role='admin').delete()
        else:
            deleted_scope, deleted_grant = admin_scope_n, admin_grant_n

        summary = (
            f'补授 {stats["ops"]} 项操作码、新增 {stats["scopes"]} 项分公司节点授权、'
            f'无变化 {stats["unchanged"]} 人、待人工 {len(manual)} 人、'
            f'清理 admin 冗余 {deleted_scope} 节点 + {deleted_grant} 操作码'
            + ('（已写入）' if apply else '（dry-run，未写库；确认后加 --apply 执行）')
        )
        self.stdout.write(self.style.SUCCESS(summary))
