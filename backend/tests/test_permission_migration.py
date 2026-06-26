"""数据迁移测试：旧 role → 管理授权种子是否保留既有能力。"""
import pytest
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
def test_migration_seeds_supervisor_region_grant(region, branch):
    """supervisor 迁移后获得其 region 授权 + 隐含操作。"""
    from apps.users.models import User

    user = User.objects.create_user(
        phone='13700000001', name='主管', password='test123456',
        role='supervisor', region=region, branch=branch,
    )
    ManagementScope.objects.filter(user=user).delete()
    OperationGrant.objects.filter(user=user).delete()

    seed_legacy_grants()

    assert ManagementScope.objects.filter(user=user, region=region).exists()
    codes = set(OperationGrant.objects.filter(user=user).values_list('code', flat=True))
    assert set(SUPERVISOR_OPERATIONS).issubset(codes)


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
