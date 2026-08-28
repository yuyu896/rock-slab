"""写单表单选项收口（拆案第 9 案）——分公司下拉范围过滤 + 台账正数列筛选。"""
import pytest
from conftest import _client_for


@pytest.mark.django_db
class TestBranchScopeWrite:
    """GET /api/branches?scope=write 按授权范围过滤；无参全量兼容。"""

    def test_scoped_user_gets_only_authorized_branches(
        self, supervisor_user, branch, second_branch,
    ):
        client = _client_for(supervisor_user)
        resp = client.get('/api/branches/', {'scope': 'write'})
        names = [b['name'] for b in resp.data]
        assert names == [branch.name]
        assert second_branch.name not in names

    def test_admin_gets_all_with_scope_write(self, admin_user, branch, second_branch):
        client = _client_for(admin_user)
        resp = client.get('/api/branches/', {'scope': 'write'})
        assert {b['name'] for b in resp.data} == {branch.name, second_branch.name}

    def test_no_scope_param_returns_all(self, supervisor_user, branch, second_branch):
        client = _client_for(supervisor_user)
        resp = client.get('/api/branches/')
        assert {b['name'] for b in resp.data} == {branch.name, second_branch.name}

    def test_unauthorized_user_gets_empty_list(self, db, branch, second_branch):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            phone='13900000099', name='无授权用户', password='test123456',
            role='staff', status='active',
        )
        client = _client_for(user)
        resp = client.get('/api/branches/', {'scope': 'write'})
        assert resp.data == []

    def test_branch_scope_write_unauthenticated_rejected(self, db, branch):
        from rest_framework.test import APIClient
        resp = APIClient().get('/api/branches/', {'scope': 'write'})
        assert resp.status_code == 401


@pytest.mark.django_db
class TestAssetStockPositiveColumn:
    """台账 positive_column 筛选：指定列 >0（品目点选按扣数列收口的数据源）。"""

    def test_stock_column_positive_filters_zero_rows(self, authenticated_client, make_stock):
        from apps.assets.services import ledger
        has_stock = make_stock(code='PC-001', qty=3, column=ledger.COLUMN_STOCK)
        in_use_only = make_stock(code='PC-002', qty=2, column=ledger.COLUMN_IN_USE)

        resp = authenticated_client.get(
            '/api/assets/summary', {'positive_column': '在库数量'},
        )
        codes = {row['资产编号'] for row in resp.data['results']}
        assert has_stock.item.asset_code in codes
        assert in_use_only.item.asset_code not in codes

        resp = authenticated_client.get(
            '/api/assets/summary', {'positive_column': '在用数量'},
        )
        codes = {row['资产编号'] for row in resp.data['results']}
        assert in_use_only.item.asset_code in codes
        assert has_stock.item.asset_code not in codes

    def test_recycle_column_positive(self, authenticated_client, make_stock):
        from apps.assets.services import ledger
        recycled = make_stock(code='PC-003', qty=1, column=ledger.COLUMN_RECYCLE)

        resp = authenticated_client.get(
            '/api/assets/summary', {'positive_column': '回收库数量'},
        )
        codes = {row['资产编号'] for row in resp.data['results']}
        assert codes == {recycled.item.asset_code}

    def test_invalid_column_rejected(self, authenticated_client, branch):
        resp = authenticated_client.get(
            '/api/assets/summary', {'positive_column': '不存在的列'},
        )
        assert resp.status_code == 400

    def test_positive_column_combines_with_branch_and_keyword(
        self, authenticated_client, make_stock,
    ):
        from apps.assets.services import ledger
        row = make_stock(code='PC-KW', qty=5, column=ledger.COLUMN_STOCK)
        # 命中 keyword 但在库为 0（在用列）——验证 keyword 与 positive_column 叠加
        make_stock(code='PC-KW2', qty=5, column=ledger.COLUMN_IN_USE)

        resp = authenticated_client.get(
            '/api/assets/summary',
            {'branch': row.branch.name, 'keyword': 'PC-KW', 'positive_column': '在库数量'},
        )
        codes = [r['资产编号'] for r in resp.data['results']]
        assert codes == ['PC-KW']
