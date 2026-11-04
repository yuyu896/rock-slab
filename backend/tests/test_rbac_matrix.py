"""
RBAC permission matrix tests — verify 5-level role access across all API endpoints.
"""
import pytest
from conftest import _client_for


def _all_clients(admin_user, manager_user, supervisor_user, leader_user, staff_user):
    return [
        ('admin', admin_user),
        ('manager', manager_user),
        ('supervisor', supervisor_user),
        ('leader', leader_user),
        ('staff', staff_user),
    ]


def _grant(user, *codes):
    from apps.permissions.models import OperationGrant

    OperationGrant.objects.bulk_create([
        OperationGrant(user=user, code=code) for code in codes
    ], ignore_conflicts=True)
    prerequisites = {
        'edit_purchase': ('view_purchase', 'view_categories'),
        'edit_assignment': ('view_assignment', 'view_asset_ledger'),
        'edit_transfer': ('view_transfer', 'view_asset_ledger'),
        'edit_recovery': ('view_recovery', 'view_asset_ledger'),
        'approve_purchase': ('view_purchase',),
        'approve_assignment': ('view_assignment',),
        'approve_internal_transfer': ('view_transfer',),
        'approve_recovery': ('view_recovery',),
        'review_inventory': ('view_inventory',),
    }
    OperationGrant.objects.bulk_create([
        OperationGrant(user=user, code=prerequisite)
        for code in codes if code in prerequisites
        for prerequisite in prerequisites[code]
    ], ignore_conflicts=True)


def _ungranted_manager():
    from apps.users.models import User

    return User.objects.create_user(
        phone='13800000099', name='无授权行政', password='test123456',
        role='manager', status='active',
    )


# ---------------------------------------------------------------------------
# Authentication endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuthRBAC:
    def test_profile_all_roles(self, admin_user, manager_user, supervisor_user, leader_user, staff_user):
        for _name, user in _all_clients(admin_user, manager_user, supervisor_user, leader_user, staff_user):
            client = _client_for(user)
            resp = client.get('/api/auth/profile/')
            assert resp.status_code == 200, f'{_name} should access profile'

    def test_unauthenticated_profile_401(self, api_client):
        resp = api_client.get('/api/auth/profile/')
        assert resp.status_code == 401

    def test_password_change_admin(self, admin_user):
        client = _client_for(admin_user)
        resp = client.put('/api/auth/password/', {
            'oldPassword': 'test123456',
            'newPassword': 'test654321',
        }, format='json')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# User management — grants control each operation independently of position.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserManagementRBAC:
    def test_list_users_requires_explicit_grant(self, db, admin_user, manager_user):
        ungranted_manager = _ungranted_manager()
        assert manager_user.role == ungranted_manager.role
        assert not ungranted_manager.operation_grants.exists()

        assert _client_for(admin_user).get('/api/users/').status_code == 200
        assert _client_for(manager_user).get('/api/users/').status_code == 200
        assert _client_for(ungranted_manager).get('/api/users/').status_code == 403

    def test_create_user_staff_forbidden(self, staff_user):
        client = _client_for(staff_user)
        resp = client.post('/api/users/', {
            'phone': '13899998888', 'name': '新用户', 'password': 'test123456',
            'role': 'staff',
        })
        assert resp.status_code == 403

    def test_create_user_leader_forbidden(self, leader_user, branch):
        # Leader has min_role='supervisor' for create, so 403
        client = _client_for(leader_user)
        resp = client.post('/api/users/', {
            'phone': '13800000011', 'name': '新专员', 'password': 'test123456',
            'role': 'staff',
        })
        assert resp.status_code == 403

    def test_create_user_retired_supervisor_cannot_assign_any_position(self, supervisor_user):
        # supervisor 已退役：不在岗位分配权线内，不能创建任何带岗位的用户
        _grant(supervisor_user, 'view_users', 'edit_users')
        client = _client_for(supervisor_user)
        resp = client.post('/api/users/', {
            'phone': '13800000013', 'name': '新组长2', 'password': 'test123456',
            'role': 'leader',
        })
        assert resp.status_code == 400

    def test_create_user_manager_can_create_leader(self, manager_user):
        _grant(manager_user, 'view_users', 'edit_users')
        client = _client_for(manager_user)
        resp = client.post('/api/users/', {
            'phone': '13800000015', 'name': '新组长3', 'password': 'test123456',
            'role': 'leader',
        })
        assert resp.status_code == 201
        from apps.users.models import User
        from apps.permissions.position_baselines import get_role_baseline
        created = User.objects.get(phone='13800000015')
        assert set(created.operation_grants.values_list('code', flat=True)) == get_role_baseline('leader')
        assert not created.management_scopes.exists()

    def test_create_user_supervisor_cannot_create_manager(self, supervisor_user):
        _grant(supervisor_user, 'view_users', 'edit_users')
        client = _client_for(supervisor_user)
        resp = client.post('/api/users/', {
            'phone': '13800000014', 'name': '新经理', 'password': 'test123456',
            'role': 'manager',
        })
        assert resp.status_code == 400

    def test_create_user_admin_can_create_any_role(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post('/api/users/', {
            'phone': '13800000015', 'name': '新管理员', 'password': 'test123456',
            'role': 'admin',
        })
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Asset management — staff read, supervisor+ write
# ---------------------------------------------------------------------------

@pytest.mark.django_db

class TestTransferRBAC:
    def test_purchase_staff_allowed(self, staff_user, branch, item_id):
        _grant(staff_user, 'edit_purchase')
        client = _client_for(staff_user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '调出分公司': '',
            '调入分公司': branch.name,
            'items': [{'item': item_id('PUR-staff'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201

    def test_purchase_supervisor_allowed(self, supervisor_user, branch, item_id):
        _grant(supervisor_user, 'edit_purchase')
        client = _client_for(supervisor_user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '调出分公司': '',
            '调入分公司': branch.name,
            'items': [{'item': item_id('PUR-sup'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201

    def test_approve_transfer_staff_forbidden(self, staff_user, admin_user, branch, item_id):
        client_admin = _client_for(admin_user)
        resp = client_admin.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '调出分公司': '',
            '调入分公司': branch.name,
            'items': [{'item': item_id('APR-001'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201
        transfer_id = resp.data['id']

        _grant(staff_user, 'view_purchase')
        client_staff = _client_for(staff_user)
        resp = client_staff.post(
            f'/api/transfers/{transfer_id}/approve', {'approved': True}, format='json',
        )
        assert resp.status_code == 403

    def test_approve_transfer_leader_forbidden(self, leader_user, admin_user, branch, item_id):
        client_admin = _client_for(admin_user)
        resp = client_admin.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '调出分公司': '',
            '调入分公司': branch.name,
            'items': [{'item': item_id('APR-002'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201
        transfer_id = resp.data['id']

        _grant(leader_user, 'view_purchase')
        client_leader = _client_for(leader_user)
        resp = client_leader.post(
            f'/api/transfers/{transfer_id}/approve', {'approved': True}, format='json',
        )
        assert resp.status_code == 403

    def test_approve_transfer_admin_allowed(self, admin_user, branch, item_id):
        # Use admin to create and approve since supervisor can't see purchases
        # (DataScopeMixin filters by from_branch__region, but purchases have no from_branch)
        client = _client_for(admin_user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '调出分公司': '',
            '调入分公司': branch.name,
            'items': [{'item': item_id('APR-003'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201
        transfer_id = resp.data['id']

        resp = client.post(f'/api/transfers/{transfer_id}/approve', {'approved': True}, format='json')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Inventory — approval restricted by role and data scope
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInventoryRBAC:
    def _create_task(self, admin_user, branch):
        # 台账底数（inventory-checklist-safety：空范围开始会被拦，submit 依赖 in_progress）
        from apps.categories.models import Category
        from apps.assets.services import ledger
        item, _ = Category.objects.get_or_create(
            asset_code='RBAC-SEED-1',
            defaults={'asset_category': '测试类目', 'item_category': '测试分类',
                      'asset_name': 'RBAC 底数品目', 'unit': '个'},
        )
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 2, '测试造数')
        client = _client_for(admin_user)
        resp = client.post('/api/inventories/', {'name': '测试盘点', 'branch': branch.id})
        assert resp.status_code == 201
        return resp.data['id']

    def test_create_task_admin(self, admin_user, branch):
        client = _client_for(admin_user)
        resp = client.post('/api/inventories/', {'name': '盘点任务', 'branch': branch.id})
        assert resp.status_code == 201

    def test_approve_inventory_staff_forbidden(self, staff_user, admin_user, branch):
        task_id = self._create_task(admin_user, branch)
        client = _client_for(admin_user)
        client.post(f'/api/inventories/{task_id}/start')
        client.post(f'/api/inventories/{task_id}/submit')

        client_staff = _client_for(staff_user)
        resp = client_staff.post(f'/api/inventories/{task_id}/approve')
        assert resp.status_code == 403

    def test_approve_inventory_leader_allowed(self, leader_user, admin_user, branch):
        _grant(leader_user, 'review_inventory')
        task_id = self._create_task(admin_user, branch)
        client = _client_for(admin_user)
        client.post(f'/api/inventories/{task_id}/start')
        client.post(f'/api/inventories/{task_id}/submit')

        client_leader = _client_for(leader_user)
        resp = client_leader.post(f'/api/inventories/{task_id}/approve')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Organization management — visibility is explicitly granted.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOrganizationRBAC:
    def test_list_regions_requires_explicit_grant(self, db, admin_user, manager_user, region):
        ungranted_manager = _ungranted_manager()
        assert manager_user.role == ungranted_manager.role

        assert _client_for(admin_user).get('/api/regions/').status_code == 200
        assert _client_for(manager_user).get('/api/regions/').status_code == 200
        assert _client_for(ungranted_manager).get('/api/regions/').status_code == 403

    def test_create_region_staff_forbidden(self, staff_user):
        client = _client_for(staff_user)
        resp = client.post('/api/regions/', {'name': '新区域', 'code': 'NEW1'})
        assert resp.status_code == 403

    def test_create_region_supervisor_forbidden(self, supervisor_user):
        client = _client_for(supervisor_user)
        resp = client.post('/api/regions/', {'name': '新区域', 'code': 'NEW2'})
        assert resp.status_code == 403

    def test_create_region_admin_allowed(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post('/api/regions/', {'name': '新区域', 'code': 'NEW3'})
        assert resp.status_code == 201

    def test_create_branch_staff_forbidden(self, staff_user, team):
        client = _client_for(staff_user)
        resp = client.post('/api/branches/', {
            'name': '新分公司', 'code': 'NW001', 'team': team.id,
        })
        assert resp.status_code == 403

    def test_create_branch_admin_allowed(self, admin_user, team):
        client = _client_for(admin_user)
        resp = client.post('/api/branches/', {
            'name': '新分公司', 'code': 'NW002', 'team': team.id,
        })
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Reports — viewing requires a specific operation grant.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportRBAC:
    def test_overview_requires_explicit_grant(self, db, admin_user, manager_user):
        ungranted_manager = _ungranted_manager()
        assert manager_user.role == ungranted_manager.role

        assert _client_for(admin_user).get('/api/reports/overview/').status_code == 200
        assert _client_for(manager_user).get('/api/reports/overview/').status_code == 200
        assert _client_for(ungranted_manager).get('/api/reports/overview/').status_code == 403

    def test_unauthenticated_overview_401(self, api_client):
        resp = api_client.get('/api/reports/overview/')
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Audit — admin only for full access, my_logs for all
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditRBAC:
    def test_list_audit_admin_allowed(self, admin_user):
        client = _client_for(admin_user)
        resp = client.get('/api/audit/')
        assert resp.status_code == 200

    def test_list_audit_staff_forbidden(self, staff_user):
        client = _client_for(staff_user)
        resp = client.get('/api/audit/')
        assert resp.status_code == 403

    def test_list_audit_supervisor_forbidden(self, supervisor_user):
        client = _client_for(supervisor_user)
        resp = client.get('/api/audit/')
        assert resp.status_code == 403

    def test_my_logs_admin_allowed(self, admin_user):
        client = _client_for(admin_user)
        resp = client.get('/api/audit/my_logs/')
        assert resp.status_code == 200

    def test_my_logs_staff_forbidden(self, staff_user):
        # AuditLogViewSet has min_role='admin' globally, my_logs doesn't override
        client = _client_for(staff_user)
        resp = client.get('/api/audit/my_logs/')
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Notifications — own data only
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotificationRBAC:
    def test_list_notifications_all_roles(self, admin_user, staff_user):
        _grant(staff_user, 'view_notifications')
        for _name, user in [('admin', admin_user), ('staff', staff_user)]:
            client = _client_for(user)
            resp = client.get('/api/notifications/')
            assert resp.status_code == 200, f'{_name} should list own notifications'

    def test_unread_count_all_roles(self, admin_user, staff_user):
        _grant(staff_user, 'view_notifications')
        for _name, user in [('admin', admin_user), ('staff', staff_user)]:
            client = _client_for(user)
            resp = client.get('/api/notifications/unread_count/')
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Categories — staff read, supervisor+ write
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCategoryRBAC:
    def test_list_categories_all_roles(self, admin_user, staff_user, category):
        _grant(staff_user, 'view_categories')
        for _name, user in [('admin', admin_user), ('staff', staff_user)]:
            client = _client_for(user)
            resp = client.get('/api/categories/')
            assert resp.status_code == 200

    def test_create_category_staff_forbidden(self, staff_user):
        client = _client_for(staff_user)
        resp = client.post('/api/categories/', {
            'asset_category': '固定', 'item_category': '办公',
            'asset_name': '测试', 'asset_code': 'CAT-001', 'unit': '台',
        })
        assert resp.status_code == 403

    def test_create_category_leader_forbidden(self, leader_user):
        client = _client_for(leader_user)
        resp = client.post('/api/categories/', {
            'asset_category': '固定', 'item_category': '办公',
            'asset_name': '测试', 'asset_code': 'CAT-002', 'unit': '台',
        })
        assert resp.status_code == 403

    def test_create_category_supervisor_allowed(self, supervisor_user):
        _grant(supervisor_user, 'create_categories')
        client = _client_for(supervisor_user)
        resp = client.post('/api/categories/', {
            'asset_category': '固定', 'item_category': '办公',
            'asset_name': '测试', 'asset_code': 'CAT-003', 'unit': '台',
        })
        assert resp.status_code == 201
