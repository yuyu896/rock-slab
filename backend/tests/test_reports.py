"""报表契约测试（P1 台账口径）：overview / by-branch / by-status / transfers / 数据范围。

总量=台账三列之和；购入金额与增长来自采购单（P2 起金额/数量按明细行聚合）。
"""
import pytest
from datetime import date
from decimal import Decimal
from rest_framework import status

from apps.transfers.models import Transfer, TransferLine
from conftest import _client_for


def _item(code):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
        },
    )
    return item


def _seed(branch, code, stock=0, in_use=0, recycle=0):
    from apps.assets.services import ledger
    item = _item(code)
    if stock:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '造数')
    if in_use:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, in_use, '造数')
    if recycle:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_RECYCLE, recycle, '造数')
    return item


def _seed_purchase(branch, code, qty, amount, when, client_user=None):
    from apps.authentication.models import ExpiringToken
    from rest_framework.test import APIClient
    client = APIClient()
    token, _ = ExpiringToken.objects.get_or_create(user=client_user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    resp = client.post('/api/transfers/purchase', {
        '调拨日期': str(when), '调出分公司': branch.name,
        'items': [{'item': str(_item(code).id), '数量': qty, '金额': str(amount)}],
    }, format='json')
    assert resp.status_code == 201, resp.data
    resp = client.post(f"/api/transfers/{resp.data['id']}/approve", {'approved': True}, format='json')
    assert resp.status_code == 200, resp.data


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportOverview:
    def test_overview_empty_database(self, authenticated_client):
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.status_code == 200
        data = resp.data
        assert data['totalAssets'] == 0
        assert data['totalValue'] == 0
        assert data['activeRate'] == 0
        assert data['growthRate'] == 0

    def test_overview_counts_ledger_totals(self, authenticated_client, branch):
        _seed(branch, 'RP-O-001', stock=3, in_use=2, recycle=1)
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.data['totalAssets'] == 6

    def test_active_rate_stock_plus_in_use(self, authenticated_client, branch):
        # 在库 3 + 在用 2，回收库 3 → 活跃率 5/8
        _seed(branch, 'RP-O-002', stock=3, in_use=2, recycle=3)
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.data['activeRate'] == 62.5

    def test_total_value_from_purchase_documents(self, authenticated_client, admin_user, branch):
        _seed(branch, 'RP-O-003', stock=1)
        _seed_purchase(branch, 'RP-O-003', 2, Decimal('1200.00'), date(2026, 8, 1), admin_user)
        resp = authenticated_client.get('/api/reports/overview/')
        assert float(resp.data['totalValue']) == 1200.0

    def test_growth_rate_with_previous_month(self, authenticated_client, admin_user, branch):
        from django.utils import timezone
        now = timezone.now()
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        _item('RP-O-004')
        _seed_purchase(branch, 'RP-O-004', 1, Decimal('100.00'), date(prev_year, prev_month, 15), admin_user)
        _seed_purchase(branch, 'RP-O-004', 2, Decimal('200.00'), date(now.year, now.month, 1), admin_user)
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.data['growthRate'] == 100.0  # (2-1)/1

    def test_value_growth_rate_month_over_month(self, authenticated_client, admin_user, branch):
        from django.utils import timezone
        now = timezone.now()
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        _item('RP-O-005')
        _seed_purchase(branch, 'RP-O-005', 1, Decimal('100.00'), date(prev_year, prev_month, 15), admin_user)
        _seed_purchase(branch, 'RP-O-005', 3, Decimal('300.00'), date(now.year, now.month, 1), admin_user)
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.data['valueGrowthRate'] == 200.0  # (300-100)/100

    def test_low_stock_count_row_and_item_levels(self, authenticated_client, branch):
        from apps.assets.models import AssetStock
        # 行级警戒线不足
        low_by_row = _seed(branch, 'RP-O-006', stock=2)
        AssetStock.objects.filter(item=low_by_row, branch=branch).update(警戒线=5)
        # 品目默认警戒线不足
        low_by_item = _item('RP-O-007')
        low_by_item.warning_line = 10
        low_by_item.save(update_fields=['warning_line'])
        from apps.assets.services import ledger
        ledger.apply_adjustment(branch, low_by_item, ledger.COLUMN_STOCK, 3, '造数')
        # 充足行（在库 ≥ 品目默认）
        ok_item = _item('RP-O-008')
        ok_item.warning_line = 1
        ok_item.save(update_fields=['warning_line'])
        ledger.apply_adjustment(branch, ok_item, ledger.COLUMN_STOCK, 5, '造数')
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.data['lowStockCount'] == 2

    def test_overview_unauthenticated(self, api_client):
        resp = api_client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# By branch / by status
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportByBranch:
    def test_by_branch_breakdown(self, authenticated_client, branch, second_branch):
        _seed(branch, 'RP-B-001', stock=6, in_use=2)
        _seed(second_branch, 'RP-B-002', stock=2)
        resp = authenticated_client.get('/api/reports/by-branch/')
        assert resp.status_code == 200
        data = {row['name']: row for row in resp.data}
        assert data[branch.name]['value'] == 8
        assert data[branch.name]['stock'] == 6
        assert data[branch.name]['inUse'] == 2
        assert data[branch.name]['recycle'] == 0
        assert data[second_branch.name]['value'] == 2

    def test_by_branch_amount_from_purchase_lines(self, authenticated_client, admin_user, branch, second_branch):
        _seed(branch, 'RP-B-003', stock=1)
        _seed(second_branch, 'RP-B-004', stock=1)
        # 两张已生效采购单均入库 branch（金额按明细行并入同名分公司）
        _seed_purchase(branch, 'RP-B-003', 1, Decimal('100.00'), date(2026, 8, 1), admin_user)
        _seed_purchase(branch, 'RP-B-003', 2, Decimal('50.00'), date(2026, 8, 2), admin_user)
        resp = authenticated_client.get('/api/reports/by-branch/')
        data = {row['name']: row for row in resp.data}
        assert float(data[branch.name]['amount']) == 150.0
        assert float(data[second_branch.name]['amount']) == 0.0
        # 采购生效后台账加量：branch 在库 1+1+2=4 / second 1 → 数量占比 80/20
        assert data[branch.name]['percentage'] == 80.0
        assert float(data[branch.name]['amountPercentage']) == 100.0

    def test_by_branch_empty(self, authenticated_client):
        resp = authenticated_client.get('/api/reports/by-branch/')
        assert resp.status_code == 200
        assert resp.data == []


@pytest.mark.django_db
class TestReportByStatus:
    def test_by_status_breakdown(self, authenticated_client, branch):
        _seed(branch, 'RP-S-001', stock=6, in_use=2, recycle=2)
        resp = authenticated_client.get('/api/reports/by-status/')
        assert resp.status_code == 200
        statuses = {row['status']: row['count'] for row in resp.data}
        assert statuses == {'在库': 6, '在用': 2, '回收库': 2}


# ---------------------------------------------------------------------------
# Transfers report
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportTransfers:
    def _make_transfer(self, branch, code, action_type, approval='已通过', operator=''):
        transfer = Transfer.objects.create(
            调拨日期=date(2026, 8, 1),
            调出分公司=branch.name, from_branch=branch,
            action_type=action_type, 审批状态=approval, 创建人=operator,
        )
        TransferLine.objects.create(
            transfer=transfer, item=_item(code), 行号=1, 数量=2,
        )
        return transfer

    def test_transfers_report_returns_data(self, authenticated_client, branch):
        self._make_transfer(branch, 'RP-T-001', 'transfer')
        resp = authenticated_client.get('/api/reports/transfers/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1
        # 报表明细按行输出：一行明细一行记录
        row = next(r for r in resp.data if r['assetCode'] == 'RP-T-001')
        assert row['quantity'] == 2
        assert 'docNumber' in row

    def test_transfers_row_includes_operator(self, authenticated_client, branch):
        self._make_transfer(branch, 'RP-T-004', 'assign', operator='张三')
        resp = authenticated_client.get('/api/reports/transfers/')
        row = next(r for r in resp.data if r['assetCode'] == 'RP-T-004')
        assert row['operator'] == '张三'

    def test_filter_by_action_type(self, authenticated_client, branch):
        self._make_transfer(branch, 'RP-T-002', 'transfer')
        self._make_transfer(branch, 'RP-T-003', 'purchase')
        resp = authenticated_client.get('/api/reports/transfers/?type=transfer')
        assert all(row['actionType'] == 'transfer' for row in resp.data)


# ---------------------------------------------------------------------------
# Data scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportDataScoping:
    def test_admin_sees_all(self, admin_user, branch, second_branch):
        _seed(branch, 'RP-D-001', stock=5)
        _seed(second_branch, 'RP-D-002', stock=7)
        client = _client_for(admin_user)
        resp = client.get('/api/reports/overview/')
        assert resp.data['totalAssets'] == 12

    def test_supervisor_sees_only_own_region(self, supervisor_user, branch, second_branch):
        _seed(branch, 'RP-D-003', stock=5)
        _seed(second_branch, 'RP-D-004', stock=7)
        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/overview/')
        assert resp.data['totalAssets'] == 5

    def test_staff_sees_only_own_branch(self, staff_user, branch, second_branch):
        _seed(branch, 'RP-D-005', stock=4)
        _seed(second_branch, 'RP-D-006', stock=9)
        client = _client_for(staff_user)
        resp = client.get('/api/reports/overview/')
        assert resp.data['totalAssets'] == 4

    def test_supervisor_by_branch_excludes_other_region(self, supervisor_user, branch, second_branch):
        _seed(branch, 'RP-D-007', stock=3)
        _seed(second_branch, 'RP-D-008', stock=8)
        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/by-branch/')
        names = {row['name'] for row in resp.data}
        assert branch.name in names
        assert second_branch.name not in names
