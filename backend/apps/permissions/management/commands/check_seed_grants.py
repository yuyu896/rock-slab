"""校验 permissions 0002 种子授权结果。

部署后（migrate 之后）执行，确认种子授权与旧 role 隐含一致；
异常时以非零状态退出，供 deploy.sh 中止部署。
"""
from django.core.management.base import BaseCommand
from apps.users.models import User
from apps.permissions.models import ManagementScope, OperationGrant
from apps.permissions.legacy_seed import SUPERVISOR_OPERATIONS, MANAGER_OPERATIONS


class Command(BaseCommand):
    help = '校验 permissions 种子授权结果（部署后验证）'

    def handle(self, *args, **options):
        errors = []
        scope_count = ManagementScope.objects.count()
        grant_count = OperationGrant.objects.count()
        self.stdout.write(f'ManagementScope 数量: {scope_count}')
        self.stdout.write(f'OperationGrant 数量: {grant_count}')

        if scope_count == 0 and grant_count == 0:
            # 仅当系统无非 admin 用户时才允许全空
            non_admin = User.objects.exclude(role='admin').count()
            if non_admin > 0:
                errors.append('存在非 admin 用户但种子授权为空，0002 种子可能未执行或失败')

        # 抽样：每个 role 取一用户核对
        for role, expected_ops in [
            ('supervisor', SUPERVISOR_OPERATIONS),
            ('manager', MANAGER_OPERATIONS),
        ]:
            user = User.objects.filter(role=role).first()
            if not user:
                self.stdout.write(f'跳过 {role}：无该角色用户')
                continue
            got = set(user.operation_grants.values_list('code', flat=True))
            missing = set(expected_ops) - got
            if missing:
                errors.append(f'{role} 用户 {user.phone} 缺少操作授权: {sorted(missing)}')
            else:
                self.stdout.write(f'[OK] {role} 用户 {user.phone} 操作授权齐全')

        # leader/staff：有 branch 的应有 branch 授权
        for role in ('leader', 'staff'):
            user = User.objects.filter(role=role, branch__isnull=False).first()
            if not user:
                self.stdout.write(f'跳过 {role}：无带 branch 的用户')
                continue
            has_branch_scope = user.management_scopes.filter(
                branch__isnull=False
            ).exists() or user.management_scopes.filter(is_all_data=True).exists()
            if not has_branch_scope:
                errors.append(f'{role} 用户 {user.phone} 有 branch 但未种子 branch 授权')
            else:
                self.stdout.write(f'[OK] {role} 用户 {user.phone} 分公司授权存在')

        # admin 不应有授权（走职位兜底）
        admin_with_grant = User.objects.filter(role='admin').filter(
            management_scopes__isnull=False
        ).exists() or User.objects.filter(role='admin').filter(
            operation_grants__isnull=False
        ).exists()
        if admin_with_grant:
            errors.append('admin 用户存在授权记录（应为空，走职位兜底）')

        # 无 region/branch 的非 admin 用户（供人工补授）
        unscoped = User.objects.exclude(role='admin').filter(
            management_scopes__isnull=True
        )
        if unscoped.exists():
            self.stdout.write(self.style.WARNING(
                f'[WARN] {unscoped.count()} 个非 admin 用户无组织节点授权（需人工在权限分配页面补授）:'
            ))
            for u in unscoped[:20]:
                self.stdout.write(f'    {u.role} | {u.phone} | {u.name}')

        if errors:
            self.stdout.write(self.style.ERROR('种子授权校验失败：'))
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [FAIL] {e}'))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('种子授权校验通过 ✓'))
