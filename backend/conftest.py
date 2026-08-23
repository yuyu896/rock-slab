"""
Pytest configuration and shared fixtures for Rock Slab backend tests.
"""
import pytest
import django
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rock_slab.settings.development')
django.setup()

User = get_user_model()

# 测试中经流转五个 action 端点使用的资产编号——P1 起编号户籍在品目字典，统一预登记。
# 未列入的编号（如校验类测试用的临时编号）仍会触发「未登记」拒绝。
TEST_ITEM_CODES = [
    'APR-001', 'APR-002', 'APR-003',
    'AST-APPROVE-001', 'AST-TEST-001', 'AST-TEST-002', 'AST-SYNC-001',
    'AUDIT-TEST-001', 'AUDIT-TEST-002',
    'BF-C1', 'DRF-001', 'DRF-002',
    'NOTIF-SCOPE-001', 'PUR-staff', 'PUR-sup',
    'SCOPE-IN-001', 'SCOPE-OUT-001', 'X-001',
] + [f'RC-{i}' for i in range(1, 9)] + [f'IM-{i}' for i in range(1, 7)] \
  + ['TRF-001', 'REC-001', 'PUR-001', 'DUP-001', 'SPE-001', 'EDT-005'] \
  + [f'SC-{i:03d}' for i in range(1, 7)] + [f'EDT-{i:03d}' for i in range(1, 5)]


@pytest.fixture(autouse=True)
def seed_test_dictionary(db):
    """为全部测试预登记常见测试品目，避免每处测试手工建字典。"""
    from apps.categories.models import Category
    for code in TEST_ITEM_CODES:
        Category.objects.get_or_create(
            asset_code=code,
            defaults={
                'asset_category': '测试类目',
                'item_category': '测试分类',
                'asset_name': f'测试品目 {code}',
                'unit': '个',
            },
        )


# ---------------------------------------------------------------------------
# API client helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    return APIClient()


def _client_for(user):
    """Return an authenticated APIClient for the given user."""
    from apps.authentication.models import ExpiringToken
    client = APIClient()
    token, _ = ExpiringToken.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Authenticated APIClient for admin_user."""
    return _client_for(admin_user)


@pytest.fixture
def manager_client(api_client, manager_user):
    """Authenticated APIClient for manager_user."""
    return _client_for(manager_user)


@pytest.fixture
def supervisor_client(api_client, supervisor_user):
    """Authenticated APIClient for supervisor_user."""
    return _client_for(supervisor_user)


@pytest.fixture
def leader_client(api_client, leader_user):
    """Authenticated APIClient for leader_user."""
    return _client_for(leader_user)


@pytest.fixture
def staff_client(api_client, staff_user):
    """Authenticated APIClient for staff_user."""
    return _client_for(staff_user)


# ---------------------------------------------------------------------------
# Organization fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def region(db):
    from apps.organizations.models import Region
    return Region.objects.create(name='测试区域', code='TEST', status='active')


@pytest.fixture
def team(db, region):
    from apps.organizations.models import Team
    return Team.objects.create(name='测试行政组', region=region, status='active')


@pytest.fixture
def branch(db, team):
    from apps.organizations.models import Branch
    return Branch.objects.create(
        name='测试分公司', code='CS001', team=team, status='active',
    )


@pytest.fixture
def second_region(db):
    from apps.organizations.models import Region
    return Region.objects.create(name='第二区域', code='REG2', status='active')


@pytest.fixture
def second_team(db, second_region):
    from apps.organizations.models import Team
    return Team.objects.create(name='第二行政组', region=second_region, status='active')


@pytest.fixture
def second_branch(db, second_team):
    from apps.organizations.models import Branch
    return Branch.objects.create(
        name='第二分公司', code='RG2001', team=second_team, status='active',
    )


# ---------------------------------------------------------------------------
# User fixtures — 5 roles
# ---------------------------------------------------------------------------
# 注：解耦后权限由 ManagementScope / OperationGrant 决定，不再由 role 推导。
# 各角色 fixture 按其"旧有效范围"种子授权，与生产数据迁移保持一致：
#   - admin           → 不种子（走职位兜底）
#   - manager         → 授权全部已知 region + 原 manager 隐含的操作
#   - supervisor      → 授权其 region + 原 supervisor 隐含的操作
#   - leader / staff  → 授权其 branch
LEGACY_OPERATIONS = {
    'manager': [
        'manage_users', 'manage_dictionary', 'manage_assets',
        'approve_transfer', 'approve_inventory',
        'view_all_notifications', 'view_reports',
    ],
    'supervisor': [
        'manage_users', 'manage_dictionary', 'manage_assets',
        'approve_transfer', 'approve_inventory',
    ],
}


def _grant_legacy_access(user, role, region=None, branch=None, extra_regions=None):
    """按旧 role 模型为用户种子管理授权（组织节点 + 业务操作）。"""
    from apps.permissions.models import ManagementScope, OperationGrant
    regions = set()
    if region is not None:
        regions.add(region.id)
    if extra_regions:
        regions.update(r.id for r in extra_regions)
    for rid in regions:
        ManagementScope.objects.get_or_create(user=user, region_id=rid)
    if branch is not None and not regions:
        ManagementScope.objects.get_or_create(user=user, branch=branch)
    for code in LEGACY_OPERATIONS.get(role, []):
        OperationGrant.objects.get_or_create(user=user, code=code)
    return user


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        phone='13900000000', name='测试管理员', password='test123456',
        role='admin', status='active',
    )


@pytest.fixture
def manager_user(db, region, second_region):
    user = User.objects.create_user(
        phone='13900000001', name='测试经理', password='test123456',
        role='manager', status='active',
    )
    # 原 manager 数据范围=全部 → 授权测试中的全部 region
    return _grant_legacy_access(user, 'manager', extra_regions=[region, second_region])


@pytest.fixture
def supervisor_user(db, region, branch):
    user = User.objects.create_user(
        phone='13900000002', name='测试主管', password='test123456',
        role='supervisor', status='active', branch=branch,
    )
    return _grant_legacy_access(user, 'supervisor', region=region, branch=branch)


@pytest.fixture
def leader_user(db, branch):
    user = User.objects.create_user(
        phone='13900000003', name='测试组长', password='test123456',
        role='leader', status='active', branch=branch,
    )
    return _grant_legacy_access(user, 'leader', branch=branch)


@pytest.fixture
def staff_user(db, branch):
    user = User.objects.create_user(
        phone='13900000004', name='测试专员', password='test123456',
        role='staff', status='active', branch=branch,
    )
    return _grant_legacy_access(user, 'staff', branch=branch)


# Second-region users for data-scoping tests

@pytest.fixture
def supervisor_b(db, second_region, second_branch):
    user = User.objects.create_user(
        phone='13900000005', name='区域B主管', password='test123456',
        role='supervisor', status='active', branch=second_branch,
    )
    return _grant_legacy_access(
        user, 'supervisor', region=second_region, branch=second_branch,
    )


@pytest.fixture
def staff_b(db, second_branch):
    user = User.objects.create_user(
        phone='13900000006', name='区域B专员', password='test123456',
        role='staff', status='active', branch=second_branch,
    )
    return _grant_legacy_access(user, 'staff', branch=second_branch)


# ---------------------------------------------------------------------------
# Category fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def category(db):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='固定资产',
        item_category='办公设备',
        asset_name='测试分类',
        asset_code='TEST-001',
        unit='台',
    )


# ---------------------------------------------------------------------------
# Asset factory helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def make_asset(branch):
    """Factory fixture to create Asset instances with sensible defaults."""
    from apps.assets.models import Asset

    counter = {'n': 0}

    def _make(**overrides):
        counter['n'] += 1
        defaults = dict(
            序号=counter['n'],
            分公司=branch.name,
            分公司编号=branch.code,
            资产编号=f'AUTO-{counter["n"]:04d}',
            资产类目='固定资产',
            物品分类='办公设备',
            资产名称=f'自动测试资产{counter["n"]}',
            数量=1,
            当前状态='在库',
            branch=branch,
        )
        defaults.update(overrides)
        return Asset.objects.create(**defaults)

    return _make


@pytest.fixture
def make_asset_b(second_branch):
    """Factory fixture to create Asset instances in the second region."""
    from apps.assets.models import Asset

    counter = {'n': 0}

    def _make(**overrides):
        counter['n'] += 1
        defaults = dict(
            序号=counter['n'] + 100,
            分公司=second_branch.name,
            分公司编号=second_branch.code,
            资产编号=f'B-AUTO-{counter["n"]:04d}',
            资产类目='固定资产',
            物品分类='办公设备',
            资产名称=f'区域B资产{counter["n"]}',
            数量=1,
            当前状态='在库',
            branch=second_branch,
        )
        defaults.update(overrides)
        return Asset.objects.create(**defaults)

    return _make
