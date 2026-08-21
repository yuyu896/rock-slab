"""数据迁移测试：旧 role → 管理授权种子是否保留既有能力。"""
import pytest
from django.test import TransactionTestCase
from apps.permissions.legacy_seed import (
    SUPERVISOR_OPERATIONS,
    MANAGER_OPERATIONS,
    seed_legacy_grants,
)
from apps.permissions.models import ManagementScope, OperationGrant


def test_role_operation_constants():
    """操作码常量与设计一致。"""
    assert 'manage_users' in SUPERVISOR_OPERATIONS
    assert 'approve_transfer' in SUPERVISOR_OPERATIONS
    assert set(SUPERVISOR_OPERATIONS).issubset(set(MANAGER_OPERATIONS))
    assert 'view_all_notifications' in MANAGER_OPERATIONS


@pytest.mark.django_db
def test_migration_seeds_supervisor_branch_grant_only(branch):
    """当前模型（无 region 列）：supervisor 仅挂分公司时种子逻辑无可推导区域，不授区域授权。"""
    from apps.users.models import User

    user = User.objects.create_user(
        phone='13700000001', name='主管', password='test123456',
        role='supervisor', branch=branch,
    )
    ManagementScope.objects.filter(user=user).delete()
    OperationGrant.objects.filter(user=user).delete()

    seed_legacy_grants()

    # region 列已删，历史种子路径（region→区域授权）只能在迁移历史模型语境中触发
    assert not ManagementScope.objects.filter(user=user).exists()
    assert not OperationGrant.objects.filter(user=user).exists()


class TestHistoricalSeedMigration(TransactionTestCase):
    """permissions.0002 历史迁移：supervisor 的 region 授权在真实迁移语境中种子。"""

    def test_supervisor_region_grant_seeded_via_migration(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        # 回退到种子迁移之前的历史状态（User 尚有 region 列）
        executor.migrate([
            ('users', '0005_alter_user_role'),
            ('organizations', '0006_company'),
            ('permissions', '0001_initial'),
        ])
        old_state = executor.loader.project_state([
            ('users', '0005_alter_user_role'),
            ('organizations', '0006_company'),
            ('permissions', '0001_initial'),
        ])
        OldUser = old_state.apps.get_model('users', 'User')
        OldRegion = old_state.apps.get_model('organizations', 'Region')
        OldTeam = old_state.apps.get_model('organizations', 'Team')
        OldBranch = old_state.apps.get_model('organizations', 'Branch')

        region = OldRegion.objects.create(name='种子区域', code='SEED1', status='active')
        branch = OldBranch.objects.create(name='种子分公司', code='SD001', region=region, status='active')
        user = OldUser.objects.create(
            phone='13700000001', name='主管', password='x',
            role='supervisor', status='active', region=region, branch=branch,
        )
        try:
            # loader 缓存 applied 状态，正向用新 executor
            forward = MigrationExecutor(connection)
            forward.migrate([('permissions', '0002_seed_grants_from_legacy_role')])

            assert ManagementScope.objects.filter(user_id=user.id, region_id=region.id).exists()
            codes = set(OperationGrant.objects.filter(user_id=user.id).values_list('code', flat=True))
            assert set(SUPERVISOR_OPERATIONS).issubset(codes)
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())


@pytest.mark.django_db
def test_migration_seeds_leader_staff_branch_grant(branch):
    """leader/staff 迁移后获得其 branch 授权（无操作码）。"""
    from apps.users.models import User

    leader = User.objects.create_user(
        phone='13700000002', name='组长', password='test123456',
        role='leader', branch=branch,
    )
    staff = User.objects.create_user(
        phone='13700000003', name='专员', password='test123456',
        role='staff', branch=branch,
    )
    seed_legacy_grants()

    assert ManagementScope.objects.filter(user=leader, branch=branch).exists()
    assert ManagementScope.objects.filter(user=staff, branch=branch).exists()
    assert not OperationGrant.objects.filter(user=leader).exists()
    assert not OperationGrant.objects.filter(user=staff).exists()


@pytest.mark.django_db
def test_migration_skips_admin():
    """admin 不被种子任何授权。"""
    from apps.users.models import User

    admin = User.objects.create_user(
        phone='13700000000', name='管理员', password='test123456', role='admin',
    )
    seed_legacy_grants()

    assert not ManagementScope.objects.filter(user=admin).exists()
    assert not OperationGrant.objects.filter(user=admin).exists()
