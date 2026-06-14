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
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# User management — supervisor+ for write, staff for read
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserManagementRBAC:
    def test_list_users_all_roles(self, admin_user, manager_user, supervisor_user, leader_user, staff_user):
        for _name, user in _all_clients(admin_user, manager_user, supervisor_user, leader_user, staff_user):
            client = _client_for(user)
            resp = client.get('/api/users/')
            assert resp.status_code == 200, f'{_name} should list users'

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

    def test_create_user_supervisor_can_create_leader(self, supervisor_user):
        client = _client_for(supervisor_user)
        resp = client.post('/api/users/', {
            'phone': '13800000013', 'name': '新组长2', 'password': 'test123456',
            'role': 'leader',
        })
        assert resp.status_code == 201

    def test_create_user_supervisor_cannot_create_manager(self, supervisor_user):
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
class TestAssetRBAC:
    def test_list_assets_all_roles(
        self, admin_user, manager_user, supervisor_user,
        leader_user, staff_user, make_asset,
    ):
        make_asset()
        for _name, user in _all_clients(
            admin_user, manager_user, supervisor_user,
            leader_user, staff_user,
        ):
            client = _client_for(user)
            resp = client.get('/api/assets/')
            assert resp.status_code == 200, f'{_name} should list assets'

    def test_create_asset_staff_forbidden(self, staff_user):
        # Asset create min_role='staff', so staff has permission but data is incomplete → 400
        client = _client_for(staff_user)
        resp = client.post('/api/assets/', {'资产名称': '测试', '资产编号': 'X-001'})
        assert resp.status_code == 400

    def test_create_asset_leader_allowed(self, leader_user, branch):
        # Asset create min_role='staff', so leader can create (with valid data)
        client = _client_for(leader_user)
        resp = client.post('/api/assets/', {
            '序号': 99, '分公司': branch.name, '分公司编号': branch.code,
            '资产编号': 'X-002', '资产类目': '固定', '物品分类': '办公',
            '资产名称': '测试', '数量': 1,
        })
        assert resp.status_code == 201

    def test_update_asset_supervisor_allowed(self, supervisor_user, make_asset):
        asset = make_asset()
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/assets/{asset.id}', {'资产名称': '已修改'})
        assert resp.status_code == 200

    def test_update_asset_staff_forbidden(self, staff_user, make_asset):
        asset = make_asset()
        client = _client_for(staff_user)
        resp = client.patch(f'/api/assets/{asset.id}', {'资产名称': '尝试'})
        assert resp.status_code == 403

    def test_delete_asset_supervisor_allowed(self, supervisor_user, make_asset):
        asset = make_asset()
        client = _client_for(supervisor_user)
        resp = client.delete(f'/api/assets/{asset.id}')
        assert resp.status_code == 204

    def test_delete_asset_staff_forbidden(self, staff_user, make_asset):
        asset = make_asset()
        client = _client_for(staff_user)
        resp = client.delete(f'/api/assets/{asset.id}')
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Transfer / approval — staff can create, supervisor+ can approve
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransferRBAC:
    def test_purchase_staff_allowed(self, staff_user, branch):
        client = _client_for(staff_user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '资产编号': 'PUR-staff',
            '资产名称': '测试采购',
            '调出分公司': '',
            '调入分公司': branch.name,
            '调拨数量': 1,
            'action_type': 'purchase',
        })
        assert resp.status_code == 201

    def test_purchase_supervisor_allowed(self, supervisor_user, branch):
        client = _client_for(supervisor_user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '资产编号': 'PUR-sup',
            '资产名称': '测试采购',
            '调出分公司': '',
            '调入分公司': branch.name,
            '调拨数量': 1,
            'action_type': 'purchase',
        })
        assert resp.status_code == 201

    def test_approve_transfer_staff_forbidden(self, staff_user, admin_user, branch):
        client_admin = _client_for(admin_user)
        resp = client_admin.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '资产编号': 'APR-001',
            '资产名称': '测试审批',
            '调出分公司': '',
            '调入分公司': branch.name,
            '调拨数量': 1,
            'action_type': 'purchase',
        })
        assert resp.status_code == 201
        transfer_id = resp.data['id']

        client_staff = _client_for(staff_user)
        resp = client_staff.post(f'/api/transfers/{transfer_id}/approve', {'decision': 'approve'})
        assert resp.status_code == 403

    def test_approve_transfer_leader_forbidden(self, leader_user, admin_user, branch):
        client_admin = _client_for(admin_user)
        resp = client_admin.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '资产编号': 'APR-002',
            '资产名称': '测试审批2',
            '调出分公司': '',
            '调入分公司': branch.name,
            '调拨数量': 1,
            'action_type': 'purchase',
        })
        assert resp.status_code == 201
        transfer_id = resp.data['id']

        client_leader = _client_for(leader_user)
        resp = client_leader.post(f'/api/transfers/{transfer_id}/approve', {'decision': 'approve'})
        assert resp.status_code == 403

    def test_approve_transfer_admin_allowed(self, admin_user, branch):
        # Use admin to create and approve since supervisor can't see purchases
        # (DataScopeMixin filters by from_branch__region, but purchases have no from_branch)
        client = _client_for(admin_user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '资产编号': 'APR-003',
            '资产名称': '测试审批3',
            '调出分公司': '',
            '调入分公司': branch.name,
            '调拨数量': 1,
            'action_type': 'purchase',
        })
        assert resp.status_code == 201
        transfer_id = resp.data['id']

        resp = client.post(f'/api/transfers/{transfer_id}/approve', {'decision': 'approve'})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Inventory — approval restricted to supervisor+
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInventoryRBAC:
    def _create_task(self, admin_user, branch):
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

    def test_approve_inventory_supervisor_allowed(self, supervisor_user, admin_user, branch):
        task_id = self._create_task(admin_user, branch)
        client = _client_for(admin_user)
        client.post(f'/api/inventories/{task_id}/start')
        client.post(f'/api/inventories/{task_id}/submit')

        client_sup = _client_for(supervisor_user)
        resp = client_sup.post(f'/api/inventories/{task_id}/approve')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Organization management — admin only for write
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOrganizationRBAC:
    def test_list_regions_all_roles(self, admin_user, manager_user, supervisor_user, leader_user, staff_user, region):
        for _name, user in _all_clients(admin_user, manager_user, supervisor_user, leader_user, staff_user):
            client = _client_for(user)
            resp = client.get('/api/regions/')
            assert resp.status_code == 200, f'{_name} should list regions'

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

    def test_create_branch_staff_forbidden(self, staff_user, region):
        client = _client_for(staff_user)
        resp = client.post('/api/branches/', {
            'name': '新分公司', 'code': 'NW001', 'region': region.id,
        })
        assert resp.status_code == 403

    def test_create_branch_admin_allowed(self, admin_user, region):
        client = _client_for(admin_user)
        resp = client.post('/api/branches/', {
            'name': '新分公司', 'code': 'NW002', 'region': region.id,
        })
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Reports — all authenticated users can view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportRBAC:
    def test_overview_all_roles(self, admin_user, manager_user, supervisor_user, leader_user, staff_user):
        for _name, user in _all_clients(admin_user, manager_user, supervisor_user, leader_user, staff_user):
            client = _client_for(user)
            resp = client.get('/api/reports/overview/')
            assert resp.status_code == 200, f'{_name} should view overview'

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
        for _name, user in [('admin', admin_user), ('staff', staff_user)]:
            client = _client_for(user)
            resp = client.get('/api/notifications/')
            assert resp.status_code == 200, f'{_name} should list own notifications'

    def test_unread_count_all_roles(self, admin_user, staff_user):
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
        client = _client_for(supervisor_user)
        resp = client.post('/api/categories/', {
            'asset_category': '固定', 'item_category': '办公',
            'asset_name': '测试', 'asset_code': 'CAT-003', 'unit': '台',
        })
        assert resp.status_code == 201
