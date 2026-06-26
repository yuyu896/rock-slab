"""
Data scoping tests — verify DataScopeMixin filters data correctly per role.
"""
import pytest
from conftest import _client_for


# ---------------------------------------------------------------------------
# Asset scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAssetScoping:
    def test_admin_sees_all_assets(self, admin_user, make_asset, make_asset_b):
        make_asset()
        make_asset_b()
        client = _client_for(admin_user)
        resp = client.get('/api/assets/')
        assert resp.data['count'] == 2

    def test_manager_sees_all_assets(self, manager_user, make_asset, make_asset_b):
        make_asset()
        make_asset_b()
        client = _client_for(manager_user)
        resp = client.get('/api/assets/')
        assert resp.data['count'] == 2

    def test_supervisor_sees_own_region_only(self, supervisor_user, make_asset, make_asset_b):
        make_asset()
        make_asset_b()
        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/')
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['分公司'] == '测试分公司'

    def test_leader_sees_own_branch_only(self, leader_user, make_asset, make_asset_b):
        make_asset()
        make_asset_b()
        client = _client_for(leader_user)
        resp = client.get('/api/assets/')
        assert resp.data['count'] == 1

    def test_staff_sees_own_branch_only(self, staff_user, make_asset, make_asset_b):
        make_asset()
        make_asset_b()
        client = _client_for(staff_user)
        resp = client.get('/api/assets/')
        assert resp.data['count'] == 1


# ---------------------------------------------------------------------------
# Transfer scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransferScoping:
    def _create_transfer(self, user, to_branch_name, code):
        client = _client_for(user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '资产编号': code,
            '资产名称': '测试',
            '调出分公司': '',
            '调入分公司': to_branch_name,
            '调拨数量': 1,
            'action_type': 'purchase',
        })
        assert resp.status_code == 201

    def test_admin_sees_all_transfers(self, admin_user, branch, second_branch):
        self._create_transfer(admin_user, branch.name, 'SC-001')
        self._create_transfer(admin_user, second_branch.name, 'SC-002')
        client = _client_for(admin_user)
        resp = client.get('/api/transfers/')
        assert resp.data['count'] == 2

    def test_supervisor_sees_own_region_transfers(self, supervisor_user, admin_user, branch, second_branch):
        # Use 'transfer' type with both from/to branches so DataScopeMixin can filter
        client_admin = _client_for(admin_user)
        # Transfer from branch to second_branch
        client_admin.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '资产编号': 'SC-003',
            '资产名称': '测试',
            '调出分公司': branch.name,
            '调入分公司': second_branch.name,
            '调拨数量': 1,
            'action_type': 'transfer',
        })
        # Transfer from second_branch to branch
        client_admin.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '资产编号': 'SC-004',
            '资产名称': '测试',
            '调出分公司': second_branch.name,
            '调入分公司': branch.name,
            '调拨数量': 1,
            'action_type': 'transfer',
        })
        client = _client_for(supervisor_user)
        resp = client.get('/api/transfers/')
        # 主管可见涉及本区域分公司的调拨（无论调出还是调入），两笔均涉及测试分公司
        assert resp.data['count'] == 2

    def test_staff_sees_own_branch_transfers(self, staff_user, admin_user, branch, second_branch):
        self._create_transfer(admin_user, branch.name, 'SC-005')
        self._create_transfer(admin_user, second_branch.name, 'SC-006')
        client = _client_for(staff_user)
        resp = client.get('/api/transfers/')
        assert resp.data['count'] == 1


# ---------------------------------------------------------------------------
# Inventory task scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInventoryScoping:
    def _create_task(self, user, branch):
        client = _client_for(user)
        resp = client.post('/api/inventories/', {'name': '盘点', 'branch': branch.id})
        assert resp.status_code == 201

    def test_admin_sees_all_tasks(self, admin_user, branch, second_branch):
        self._create_task(admin_user, branch)
        self._create_task(admin_user, second_branch)
        client = _client_for(admin_user)
        resp = client.get('/api/inventories/')
        assert resp.data['count'] == 2

    def test_supervisor_sees_own_region_tasks(self, supervisor_user, admin_user, branch, second_branch):
        self._create_task(admin_user, branch)
        self._create_task(admin_user, second_branch)
        client = _client_for(supervisor_user)
        resp = client.get('/api/inventories/')
        assert resp.data['count'] == 1

    def test_staff_sees_own_branch_tasks(self, staff_user, admin_user, branch, second_branch):
        self._create_task(admin_user, branch)
        self._create_task(admin_user, second_branch)
        client = _client_for(staff_user)
        resp = client.get('/api/inventories/')
        assert resp.data['count'] == 1


# ---------------------------------------------------------------------------
# Report scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportScoping:
    def test_overview_scoped_by_region(self, supervisor_user, make_asset, make_asset_b):
        make_asset(数量=3)
        make_asset_b(数量=5)
        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/overview/')
        assert resp.status_code == 200
        assert resp.data['totalAssets'] == 1

    def test_overview_scoped_by_branch(self, staff_user, make_asset, make_asset_b):
        make_asset()
        make_asset_b()
        client = _client_for(staff_user)
        resp = client.get('/api/reports/overview/')
        assert resp.status_code == 200
        assert resp.data['totalAssets'] == 1

    def test_by_branch_scoped(self, supervisor_user, make_asset, make_asset_b):
        make_asset()
        make_asset_b()
        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/by-branch/')
        assert resp.status_code == 200
        branch_names = [item['name'] for item in resp.data]
        assert '测试分公司' in branch_names
        assert '第二分公司' not in branch_names


# ---------------------------------------------------------------------------
# User listing scoping — UserViewSet returns all users for list/retrieve;
# scoping only applies to write operations via _get_user_queryset.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserScoping:
    def test_list_returns_all_users(self, admin_user, supervisor_user, staff_user, supervisor_b, staff_b):
        # UserViewSet.get_queryset returns all users for list action
        client = _client_for(admin_user)
        resp = client.get('/api/users/')
        phones = [u['phone'] for u in resp.data]
        assert len(resp.data) >= 5
        assert supervisor_user.phone in phones
        assert supervisor_b.phone in phones
        assert staff_user.phone in phones
        assert staff_b.phone in phones
