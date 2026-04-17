"""
Pytest configuration and shared fixtures for Rock Slab backend tests.
"""
import pytest
import django
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

# Ensure Django is set up before importing models
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rock_slab.settings.development')
django.setup()

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an APIClient instance."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create and return a super admin user."""
    return User.objects.create_user(
        phone='13900000000',
        name='测试管理员',
        password='test123456',
        role='admin',
        status='active',
    )


@pytest.fixture
def manager_user(db):
    """Create and return a manager user."""
    return User.objects.create_user(
        phone='13900000001',
        name='测试经理',
        password='test123456',
        role='manager',
        status='active',
    )


@pytest.fixture
def supervisor_user(db, region, branch):
    """Create and return a supervisor user."""
    return User.objects.create_user(
        phone='13900000002',
        name='测试主管',
        password='test123456',
        role='supervisor',
        status='active',
        region=region,
        branch=branch,
    )


@pytest.fixture
def staff_user(db, branch):
    """Create and return a staff user."""
    return User.objects.create_user(
        phone='13900000004',
        name='测试专员',
        password='test123456',
        role='staff',
        status='active',
        branch=branch,
    )


@pytest.fixture
def region(db):
    """Create and return a test region."""
    from apps.organizations.models import Region
    return Region.objects.create(
        name='测试区域',
        code='TEST',
        status='active',
    )


@pytest.fixture
def branch(db, region):
    """Create and return a test branch."""
    from apps.organizations.models import Branch
    return Branch.objects.create(
        name='测试分公司',
        code='TEST-001',
        region=region,
        status='active',
    )


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Return an authenticated APIClient for admin_user."""
    from apps.authentication.models import ExpiringToken
    token, _ = ExpiringToken.objects.get_or_create(user=admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client


@pytest.fixture
def staff_client(api_client, staff_user):
    """Return an authenticated APIClient for staff_user."""
    from apps.authentication.models import ExpiringToken
    token, _ = ExpiringToken.objects.get_or_create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client
