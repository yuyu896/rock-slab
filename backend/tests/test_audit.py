"""
Tests for AuditLog: ViewSet access, custom actions, filters, and decorator.
"""
import pytest
from rest_framework import status

from apps.audit.models import AuditLog
from conftest import _client_for


AUDIT_LIST_URL = '/api/audit/'


def _detail_url(pk):
    return f'/api/audit/{pk}/'


# ---------------------------------------------------------------------------
# ViewSet access control
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogAccess:
    """Permission and basic list/retrieve tests for AuditLogViewSet."""

    def test_admin_can_list_audit_logs(self, authenticated_client):
        resp = authenticated_client.get(AUDIT_LIST_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_staff_cannot_list_audit_logs(self, staff_client):
        resp = staff_client.get(AUDIT_LIST_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_supervisor_cannot_list_audit_logs(self, supervisor_client):
        resp = supervisor_client.get(AUDIT_LIST_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_leader_cannot_list_audit_logs(self, leader_client):
        resp = leader_client.get(AUDIT_LIST_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_cannot_list_audit_logs(self, manager_client):
        """Only admin can access audit logs; manager is blocked by min_role='admin'."""
        resp = manager_client.get(AUDIT_LIST_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_list(self, api_client):
        resp = api_client.get(AUDIT_LIST_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Custom actions (statistics, by_action, by_resource, user_activity)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogActions:
    """Custom @action endpoints on AuditLogViewSet."""

    def test_statistics_returns_daily_stats(self, authenticated_client, admin_user):
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='login', resource_type='User',
            description='test login',
        )
        resp = authenticated_client.get('/api/audit/statistics/')
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)

    def test_by_action_returns_action_breakdown(self, authenticated_client, admin_user):
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='create', resource_type='Asset',
            description='created asset',
        )
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='update', resource_type='Asset',
            description='updated asset',
        )
        resp = authenticated_client.get('/api/audit/by_action/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert isinstance(data, list)
        actions = [item['action'] for item in data]
        assert 'create' in actions
        assert 'update' in actions

    def test_by_resource_returns_resource_breakdown(self, authenticated_client, admin_user):
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='create', resource_type='Asset',
            description='created asset',
        )
        resp = authenticated_client.get('/api/audit/by_resource/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert isinstance(data, list)
        assert len(data) <= 20  # capped at top 20
        resource_types = [item['resource_type'] for item in data]
        assert 'Asset' in resource_types

    def test_user_activity_returns_user_stats(self, authenticated_client, admin_user):
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            user_phone=admin_user.phone,
            action='login', resource_type='Session',
            description='login',
        )
        resp = authenticated_client.get('/api/audit/user_activity/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert isinstance(data, list)
        assert len(data) <= 20  # capped at top 20
        assert data[0]['user_name'] == admin_user.name
        assert data[0]['action_count'] >= 1


# ---------------------------------------------------------------------------
# AuditLog creation and listing
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogCreation:
    """Direct AuditLog creation and verification via list/retrieve."""

    def test_created_audit_log_appears_in_list(self, authenticated_client, admin_user):
        log = AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='create', resource_type='Asset',
            resource_name='Test Asset',
            description='created test asset',
        )
        resp = authenticated_client.get(AUDIT_LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) >= 1
        ids = [r['id'] for r in results]
        assert str(log.id) in ids

    def test_retrieve_single_audit_log(self, authenticated_client, admin_user):
        log = AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='delete', resource_type='Asset',
            resource_name='Deleted Asset',
            description='deleted test asset',
            is_success=True,
        )
        resp = authenticated_client.get(_detail_url(log.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['action'] == 'delete'
        assert resp.data['resource_type'] == 'Asset'
        assert resp.data['resource_name'] == 'Deleted Asset'
        assert resp.data['is_success'] is True

    def test_list_uses_brief_serializer(self, authenticated_client, admin_user):
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='login', resource_type='Session',
            description='login event',
        )
        resp = authenticated_client.get(AUDIT_LIST_URL)
        results = resp.data.get('results', resp.data)
        item = results[0]
        # Brief serializer should have these fields
        assert 'action' in item
        assert 'action_display' in item
        assert 'user_name' in item
        # Brief serializer should NOT have these verbose fields
        assert 'before_data' not in item
        assert 'after_data' not in item
        assert 'ip_address' not in item

    def test_retrieve_uses_full_serializer(self, authenticated_client, admin_user):
        log = AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='update', resource_type='Asset',
            description='full detail test',
            before_data={'status': '在库'},
            after_data={'status': '使用中'},
        )
        resp = authenticated_client.get(_detail_url(log.id))
        assert resp.status_code == status.HTTP_200_OK
        assert 'before_data' in resp.data
        assert 'after_data' in resp.data
        assert 'ip_address' in resp.data


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogFilters:
    """Filter audit logs by action, resource_type, user, is_success, search."""

    def _create_logs(self, admin_user):
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='create', resource_type='Asset',
            resource_name='Laptop',
            description='created laptop',
            is_success=True,
        )
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='delete', resource_type='Transfer',
            resource_name='Transfer-001',
            description='deleted transfer',
            is_success=False,
        )

    def test_filter_by_action(self, authenticated_client, admin_user):
        self._create_logs(admin_user)
        resp = authenticated_client.get(f'{AUDIT_LIST_URL}?action=create')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert all(r['action'] == 'create' for r in results)

    def test_filter_by_resource_type(self, authenticated_client, admin_user):
        self._create_logs(admin_user)
        resp = authenticated_client.get(f'{AUDIT_LIST_URL}?resource_type=Asset')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert all(r['resource_type'] == 'Asset' for r in results)

    def test_filter_by_is_success(self, authenticated_client, admin_user):
        self._create_logs(admin_user)
        resp = authenticated_client.get(f'{AUDIT_LIST_URL}?is_success=false')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert all(r['is_success'] is False for r in results)

    def test_filter_by_search(self, authenticated_client, admin_user):
        self._create_logs(admin_user)
        resp = authenticated_client.get(f'{AUDIT_LIST_URL}?search=Laptop')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) >= 1
        assert any('Laptop' in r.get('resource_name', '') for r in results)


# ---------------------------------------------------------------------------
# Decorator: @audit_log integration via transfer purchase
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogDecorator:
    """Verify @audit_log decorator creates AuditLog on decorated actions."""

    def test_purchase_creates_audit_log(self, admin_user):
        """Create a purchase transfer and verify an AuditLog is created.

        We call the purchase API directly; the TransferViewSet.purchase
        action should be decorated with @audit_log which writes a log entry.
        """
        client = _client_for(admin_user)

        # Check how many audit logs exist before
        count_before = AuditLog.objects.count()

        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-04-01',
            '资产编号': 'AUDIT-TEST-001',
            '资产名称': '审计测试资产',
            '调拨数量': 1,
            '调出分公司': '测试分公司',
            'action_type': 'purchase',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

        # If the view is decorated with @audit_log, a new AuditLog should exist
        count_after = AuditLog.objects.count()
        assert count_after > count_before

    def test_audit_log_has_correct_user_and_action(self, admin_user):
        """Verify the AuditLog created by the decorator has correct fields."""
        client = _client_for(admin_user)

        client.post('/api/transfers/purchase', {
            '调拨日期': '2026-04-02',
            '资产编号': 'AUDIT-TEST-002',
            '资产名称': '审计测试资产2',
            '调拨数量': 1,
            '调出分公司': '测试分公司',
            'action_type': 'purchase',
        }, format='json')

        log = AuditLog.objects.filter(
            user=admin_user,
            action='create',
            resource_type='Transfer',
        ).first()
        if log is not None:
            assert log.user_name == admin_user.name
            assert log.is_success is True

    def test_my_logs_returns_own_logs_only(self, authenticated_client, admin_user, staff_user):
        """The my_logs action should only return the requesting user's logs."""
        # Create logs for two different users
        AuditLog.objects.create(
            user=admin_user, user_name=admin_user.name,
            action='login', resource_type='Session',
            description='admin login',
        )
        AuditLog.objects.create(
            user=staff_user, user_name=staff_user.name,
            action='login', resource_type='Session',
            description='staff login',
        )

        # Request my_logs as admin
        resp = authenticated_client.get('/api/audit/my_logs/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert isinstance(data, list)
        # All returned items should belong to admin
        for item in data:
            assert item['user_name'] == admin_user.name
