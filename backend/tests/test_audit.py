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
# Data-scope filtering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogScope:
    """Data scope and historical grants do not replace the admin role check."""

    @staticmethod
    def _grant_audit_view(user):
        from apps.permissions.models import OperationGrant

        OperationGrant.objects.get_or_create(user=user, code='view_audit_logs')

    def test_legacy_view_grant_does_not_bypass_admin_only_list(
        self, staff_user, staff_b,
    ):
        self._grant_audit_view(staff_user)
        in_scope = AuditLog.objects.create(
            user=staff_user,
            user_name=staff_user.name,
            action='update',
            resource_type='User',
            resource_id=staff_user.id,
            resource_name='范围内员工',
        )
        out_of_scope = AuditLog.objects.create(
            user=staff_b,
            user_name=staff_b.name,
            action='update',
            resource_type='User',
            resource_id=staff_b.id,
            resource_name='范围外员工',
        )
        unmapped = AuditLog.objects.create(
            user=staff_user,
            user_name=staff_user.name,
            action='login',
            resource_type='Session',
            resource_name='登录',
        )

        response = _client_for(staff_user).get(AUDIT_LIST_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_legacy_view_grant_does_not_bypass_admin_only_detail(self, staff_user):
        self._grant_audit_view(staff_user)
        log = AuditLog.objects.create(
            user=staff_user,
            user_name=staff_user.name,
            action='update',
            resource_type='User',
            resource_id=staff_user.id,
            before_data={'branch_id': str(staff_user.branch_id), 'secret': 'before'},
            after_data={'branch_id': str(staff_user.branch_id), 'secret': 'after'},
        )

        response = _client_for(staff_user).get(_detail_url(log.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_all_data_scope_does_not_bypass_admin_only_list(
        self, db, branch, staff_user, staff_b,
    ):
        from apps.permissions.models import ManagementScope, OperationGrant
        from apps.users.models import User

        reader = User.objects.create_user(
            phone='13900000992',
            name='全组织审计查看员',
            password='test123456',
            role='manager',
            status='active',
            branch=branch,
        )
        OperationGrant.objects.create(user=reader, code='view_audit_logs')
        ManagementScope.objects.create(user=reader, is_all_data=True)
        in_branch = AuditLog.objects.create(
            user=staff_user,
            user_name=staff_user.name,
            action='update',
            resource_type='User',
            resource_id=staff_user.id,
        )
        other_branch = AuditLog.objects.create(
            user=staff_b,
            user_name=staff_b.name,
            action='update',
            resource_type='User',
            resource_id=staff_b.id,
        )
        unmapped = AuditLog.objects.create(
            user=staff_user,
            user_name=staff_user.name,
            action='login',
            resource_type='Session',
        )

        response = _client_for(reader).get(AUDIT_LIST_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_all_data_scope_does_not_bypass_admin_only_detail(self, db, branch):
        from apps.permissions.models import ManagementScope, OperationGrant
        from apps.users.models import User

        reader = User.objects.create_user(
            phone='13900000993',
            name='全组织审计详情查看员',
            password='test123456',
            role='manager',
            status='active',
            branch=branch,
        )
        OperationGrant.objects.create(user=reader, code='view_audit_logs')
        ManagementScope.objects.create(user=reader, is_all_data=True)
        log = AuditLog.objects.create(
            user=reader,
            user_name=reader.name,
            action='update',
            resource_type='Session',
            before_data={'secret': 'before'},
            after_data={'secret': 'after'},
        )

        response = _client_for(reader).get(_detail_url(log.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_sees_unmapped_logs(self, admin_user):
        log = AuditLog.objects.create(
            user=admin_user,
            user_name=admin_user.name,
            action='login',
            resource_type='Session',
        )

        response = _client_for(admin_user).get(AUDIT_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert str(log.id) in {row['id'] for row in results}

    def test_admin_can_read_historical_return_audit_log(self, admin_user, branch):
        from apps.transfers.models import Transfer

        transfer = Transfer.objects.create(
            单据编号='RET-HIST-AUDIT',
            调拨日期='2026-02-02',
            调入分公司=branch.name,
            to_branch=branch,
            action_type=Transfer.ACTION_RETURN,
            审批状态='已通过',
        )
        log = AuditLog.objects.create(
            user=admin_user,
            user_name=admin_user.name,
            action='update',
            resource_type='Transfer',
            resource_id=str(transfer.id),
            resource_name='历史归还单',
        )

        client = _client_for(admin_user)
        response = client.get(AUDIT_LIST_URL)
        detail = client.get(_detail_url(log.id))

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert str(log.id) in {row['id'] for row in results}
        assert detail.status_code == status.HTTP_200_OK
        assert detail.data['resource_id'] == str(transfer.id)

    def test_full_scope_without_audit_grant_is_denied(self, db, branch):
        from apps.permissions.models import ManagementScope
        from apps.users.models import User

        reader = User.objects.create_user(
            phone='13900000994',
            name='无审计权限全组织用户',
            password='test123456',
            role='manager',
            status='active',
            branch=branch,
        )
        ManagementScope.objects.create(user=reader, is_all_data=True)

        response = _client_for(reader).get(AUDIT_LIST_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_legacy_audit_grant_cannot_access_any_read_endpoint(self, staff_user):
        self._grant_audit_view(staff_user)
        log = AuditLog.objects.create(
            user=staff_user,
            user_name=staff_user.name,
            action='update',
            resource_type='Session',
        )
        client = _client_for(staff_user)
        endpoints = [
            AUDIT_LIST_URL,
            _detail_url(log.id),
            '/api/audit/statistics/',
            '/api/audit/by_action/',
            '/api/audit/by_resource/',
            '/api/audit/user_activity/',
            '/api/audit/my_logs/',
        ]

        for endpoint in endpoints:
            assert client.get(endpoint).status_code == status.HTTP_403_FORBIDDEN


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

    def test_purchase_creates_audit_log(self, admin_user, branch):
        """Create a purchase transfer and verify an AuditLog is created.

        We call the purchase API directly; the TransferViewSet.purchase
        action should be decorated with @audit_log which writes a log entry.
        """
        from apps.categories.models import Category
        client = _client_for(admin_user)

        # Check how many audit logs exist before
        count_before = AuditLog.objects.count()

        item = Category.objects.get(asset_code='AUDIT-TEST-001')
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-04-01',
            '调出分公司': branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

        # If the view is decorated with @audit_log, a new AuditLog should exist
        count_after = AuditLog.objects.count()
        assert count_after > count_before

    def test_audit_log_has_correct_user_and_action(self, admin_user, branch):
        """Verify the AuditLog created by the decorator has correct fields.

        The purchase action is decorated with @audit_log(action='purchase',
        resource_type='Transfer'), so the log records action='purchase'.
        """
        from apps.categories.models import Category
        client = _client_for(admin_user)

        item = Category.objects.get(asset_code='AUDIT-TEST-002')
        client.post('/api/transfers/purchase', {
            '调拨日期': '2026-04-02',
            '调出分公司': branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }, format='json')

        log = AuditLog.objects.filter(
            user=admin_user,
            action='purchase',
            resource_type='Transfer',
        ).first()
        assert log is not None
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


# ---------------------------------------------------------------------------
# 敏感字段脱敏（audit-sensitive-masking）：密码哈希不得入库/出库
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSensitiveMasking:
    def test_user_update_snapshot_masks_password(self, authenticated_client, staff_user):
        import json
        resp = authenticated_client.patch(f'/api/users/{staff_user.id}', {'name': '脱敏验证'})
        assert resp.status_code == status.HTTP_200_OK
        log = AuditLog.objects.filter(
            action='update', resource_type='User', resource_id=staff_user.id,
        ).order_by('-created_at').first()
        assert log is not None
        # 键保留（「涉及密码字段」仍可审计），值替换为掩码，哈希串不得出现
        assert log.before_data.get('password') == '***'
        assert '_state' not in log.before_data
        assert 'pbkdf2_sha256$' not in json.dumps(log.before_data, default=str)
        assert 'pbkdf2_sha256$' not in json.dumps(log.after_data or {}, default=str)

    def test_mask_sensitive_nested_and_idempotent(self):
        from apps.audit.utils import mask_sensitive
        data = {
            'password': 'pbkdf2_sha256$260000$salt$hash',
            'phone': '13900000000',
            '_state': 'django-internal',
            'profile': {
                'tokens': [{'password': 'argon2$legacy$secret'}],
                'user_phone': '13900000001',
                'note': 'x',
            },
        }
        out = mask_sensitive(data)
        assert out['password'] == '***'
        assert out['phone'] == ''
        assert out['profile']['tokens'][0]['password'] == '***'
        assert out['profile']['user_phone'] == ''
        assert out['profile']['note'] == 'x'
        assert '_state' not in out
        assert mask_sensitive(out) == out  # 幂等

    def test_backfill_migration_scrubs_legacy_rows(self, db):
        # 直接调用 0002 迁移的 RunPython 函数本体（SQLite 测试事务内无法反向
        # 迁移走完整 migrate 路径，接线为标准 RunPython、部署时自然执行）
        import importlib
        from django.apps import apps as global_apps
        migration = importlib.import_module(
            'apps.audit.migrations.0002_mask_sensitive_fields'
        )
        legacy = AuditLog.objects.create(
            action='update', resource_type='User', resource_name='历史用户',
            before_data={'password': 'pbkdf2_sha256$legacy$salt$hash', 'name': '张三'},
            after_data={'password': 'pbkdf2_sha256$legacy2$salt$hash'},
        )
        migration.scrub_audit_rows(global_apps, None)
        log = AuditLog.objects.get(id=legacy.id)
        assert log.before_data['password'] == '***'
        assert log.before_data['name'] == '张三'
        assert log.after_data['password'] == '***'
        # 幂等：重复清洗结果不变
        migration.scrub_audit_rows(global_apps, None)
        log = AuditLog.objects.get(id=legacy.id)
        assert log.before_data['password'] == '***' and log.before_data['name'] == '张三'
