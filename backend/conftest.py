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
def branch(db, region):
    from apps.organizations.models import Branch
    return Branch.objects.create(
        name='测试分公司', code='CS001', region=region, status='active',
    )


@pytest.fixture
def second_region(db):
    from apps.organizations.models import Region
    return Region.objects.create(name='第二区域', code='REG2', status='active')


@pytest.fixture
def second_branch(db, second_region):
    from apps.organizations.models import Branch
    return Branch.objects.create(
        name='第二分公司', code='RG2001', region=second_region, status='active',
    )


# ---------------------------------------------------------------------------
# User fixtures — 5 roles
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        phone='13900000000', name='测试管理员', password='test123456',
        role='admin', status='active',
    )


@pytest.fixture
def manager_user(db):
    return User.objects.create_user(
        phone='13900000001', name='测试经理', password='test123456',
        role='manager', status='active',
    )


@pytest.fixture
def supervisor_user(db, region, branch):
    return User.objects.create_user(
        phone='13900000002', name='测试主管', password='test123456',
        role='supervisor', status='active', region=region, branch=branch,
    )


@pytest.fixture
def leader_user(db, branch):
    return User.objects.create_user(
        phone='13900000003', name='测试组长', password='test123456',
        role='leader', status='active', branch=branch,
    )


@pytest.fixture
def staff_user(db, branch):
    return User.objects.create_user(
        phone='13900000004', name='测试专员', password='test123456',
        role='staff', status='active', branch=branch,
    )


# Second-region users for data-scoping tests

@pytest.fixture
def supervisor_b(db, second_region, second_branch):
    return User.objects.create_user(
        phone='13900000005', name='区域B主管', password='test123456',
        role='supervisor', status='active', region=second_region, branch=second_branch,
    )


@pytest.fixture
def staff_b(db, second_branch):
    return User.objects.create_user(
        phone='13900000006', name='区域B专员', password='test123456',
        role='staff', status='active', branch=second_branch,
    )


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
