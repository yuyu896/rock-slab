"""
Data scoping tests — verify DataScopeMixin filters data correctly per role.
"""
import pytest
from conftest import _client_for


# ---------------------------------------------------------------------------
# Asset scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStockScoping:
    """台账行数据范围（Asset 退役后由台账承接 scoping 契约）。"""

    def test_admin_sees_all(self, admin_user, make_stock, make_stock_b):
        make_stock()
        make_stock_b()
        client = _client_for(admin_user)
        resp = client.get('/api/assets/summary')
        assert resp.data['count'] == 2

    def test_manager_sees_all(self, manager_user, make_stock, make_stock_b):
        make_stock()
        make_stock_b()
        client = _client_for(manager_user)
        resp = client.get('/api/assets/summary')
        assert resp.data['count'] == 2

    def test_supervisor_sees_own_region_only(self, supervisor_user, make_stock, make_stock_b):
        make_stock()
        make_stock_b()
        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/summary')
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['branch_name'] == '测试分公司'

    def test_leader_sees_own_branch_only(self, leader_user, make_stock, make_stock_b):
        make_stock()
        make_stock_b()
        client = _client_for(leader_user)
        resp = client.get('/api/assets/summary')
        assert resp.data['count'] == 1

    def test_staff_sees_own_branch_only(self, staff_user, make_stock, make_stock_b):
        make_stock()
        make_stock_b()
        client = _client_for(staff_user)
        resp = client.get('/api/assets/summary')
        assert resp.data['count'] == 1


# ---------------------------------------------------------------------------
# Transfer scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransferScoping:
    def _create_transfer(self, user, to_branch_name, code, item_id):
        client = _client_for(user)
        resp = client.post('/api/transfers/purchase', {
            '调拨日期': '2026-01-15',
            '调出分公司': '',
            '调入分公司': to_branch_name,
            'items': [{'item': item_id(code), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201

    def test_admin_sees_all_transfers(self, admin_user, branch, second_branch, item_id):
        self._create_transfer(admin_user, branch.name, 'SC-001', item_id)
        self._create_transfer(admin_user, second_branch.name, 'SC-002', item_id)
        client = _client_for(admin_user)
        resp = client.get('/api/transfers/')
        assert resp.data['count'] == 2

    def test_supervisor_sees_own_region_transfers(
        self, supervisor_user, admin_user, branch, second_branch, item_id,
    ):
        # Use 'transfer' type with both from/to branches so DataScopeMixin can filter
        client_admin = _client_for(admin_user)
        # Transfer from branch to second_branch
        client_admin.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '调出分公司': branch.name,
            '调入分公司': second_branch.name,
            'items': [{'item': item_id('SC-003'), '数量': 1}],
        }, format='json')
        # Transfer from second_branch to branch
        client_admin.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '调出分公司': second_branch.name,
            '调入分公司': branch.name,
            'items': [{'item': item_id('SC-004'), '数量': 1}],
        }, format='json')
        client = _client_for(supervisor_user)
        resp = client.get('/api/transfers/')
        # 主管可见涉及本区域分公司的调拨（无论调出还是调入），两笔均涉及测试分公司
        assert resp.data['count'] == 2

    def test_staff_sees_own_branch_transfers(self, staff_user, admin_user, branch, second_branch, item_id):
        self._create_transfer(admin_user, branch.name, 'SC-005', item_id)
        self._create_transfer(admin_user, second_branch.name, 'SC-006', item_id)
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
    """P1 台账口径的报表范围（与 test_reports.TestReportDataScoping 互补）。"""

    def _seed(self, branch, code, qty):
        from apps.categories.models import Category
        from apps.assets.services import ledger
        item, _ = Category.objects.get_or_create(
            asset_code=code,
            defaults={'asset_category': 't', 'item_category': 't', 'asset_name': code, 'unit': '个'},
        )
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, qty, '造数')

    def test_overview_scoped_by_region(self, supervisor_user, branch, second_branch):
        self._seed(branch, 'SC-REP-001', 3)
        self._seed(second_branch, 'SC-REP-002', 5)
        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/overview/')
        assert resp.status_code == 200
        assert resp.data['totalAssets'] == 3

    def test_overview_scoped_by_branch(self, staff_user, branch, second_branch):
        self._seed(branch, 'SC-REP-003', 3)
        self._seed(second_branch, 'SC-REP-004', 5)
        client = _client_for(staff_user)
        resp = client.get('/api/reports/overview/')
        assert resp.status_code == 200
        assert resp.data['totalAssets'] == 3

    def test_by_branch_scoped(self, supervisor_user, branch, second_branch):
        self._seed(branch, 'SC-REP-005', 2)
        self._seed(second_branch, 'SC-REP-006', 7)
        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/by-branch/')
        assert resp.status_code == 200
        branch_names = [item['name'] for item in resp.data]
        assert branch.name in branch_names
        assert second_branch.name not in branch_names


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
