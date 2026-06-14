"""
Tests for Reports: overview, by-branch, by-status, transfers, and data scoping.
"""
import pytest
from datetime import date
from decimal import Decimal
from rest_framework import status

from apps.assets.models import Asset
from apps.transfers.models import Transfer
from conftest import _client_for


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportOverview:
    """GET /api/reports/overview/ — totalAssets, totalValue, activeRate, growthRate."""

    def test_overview_empty_database(self, authenticated_client):
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert data['totalAssets'] == 0
        assert data['totalValue'] == 0
        assert data['activeRate'] == 0
        assert data['growthRate'] == 0

    def test_overview_with_assets(self, authenticated_client, make_asset):
        make_asset(购入金额=Decimal('1000.00'), 当前状态='在库')
        make_asset(购入金额=Decimal('2000.00'), 当前状态='使用中')
        make_asset(购入金额=Decimal('500.00'), 当前状态='报废')

        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert data['totalAssets'] == 3
        assert float(data['totalValue']) == 3500.0

    def test_active_rate_calculation(self, authenticated_client, make_asset):
        # 2 active (在库 + 使用中) out of 4 total = 50%
        make_asset(当前状态='在库')
        make_asset(当前状态='使用中')
        make_asset(当前状态='维修中')
        make_asset(当前状态='报废')

        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['activeRate'] == 50.0

    def test_growth_rate_with_previous_month(self, authenticated_client, make_asset):
        from django.utils import timezone
        now = timezone.now()
        # Create one asset in the previous month
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        make_asset(入库日期=date(prev_year, prev_month, 15))
        # Create two assets this month
        make_asset(入库日期=date(now.year, now.month, 1))
        make_asset(入库日期=date(now.year, now.month, 5))

        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_200_OK
        # growthRate = ((2 - 1) / 1) * 100 = 100.0
        assert resp.data['growthRate'] == 100.0

    def test_overview_unauthenticated(self, api_client):
        resp = api_client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# By branch
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportByBranch:
    """GET /api/reports/by-branch/ — branch breakdown with percentages."""

    def test_by_branch_breakdown(self, authenticated_client, branch, second_branch):
        Asset.objects.create(
            序号=1, 分公司=branch.name, 分公司编号=branch.code,
            资产编号='BR-001', 资产类目='固定资产', 物品分类='办公设备',
            资产名称='Branch Asset 1', 数量=1, 当前状态='在库', branch=branch,
        )
        Asset.objects.create(
            序号=2, 分公司=branch.name, 分公司编号=branch.code,
            资产编号='BR-002', 资产类目='固定资产', 物品分类='办公设备',
            资产名称='Branch Asset 2', 数量=1, 当前状态='在库', branch=branch,
        )
        Asset.objects.create(
            序号=3, 分公司=second_branch.name, 分公司编号=second_branch.code,
            资产编号='BR-003', 资产类目='固定资产', 物品分类='办公设备',
            资产名称='Branch Asset 3', 数量=1, 当前状态='在库', branch=second_branch,
        )

        resp = authenticated_client.get('/api/reports/by-branch/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify percentages sum to ~100
        total_pct = sum(item['percentage'] for item in data)
        assert abs(total_pct - 100.0) < 0.1

        # The branch with 2 assets should come first (ordered by -count)
        assert data[0]['value'] == 2
        assert data[1]['value'] == 1

    def test_by_branch_empty(self, authenticated_client):
        resp = authenticated_client.get('/api/reports/by-branch/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []


# ---------------------------------------------------------------------------
# By status
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportByStatus:
    """GET /api/reports/by-status/ — status breakdown."""

    def test_by_status_breakdown(self, authenticated_client, make_asset):
        make_asset(当前状态='在库')
        make_asset(当前状态='在库')
        make_asset(当前状态='使用中')
        make_asset(当前状态='报废')

        resp = authenticated_client.get('/api/reports/by-status/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert isinstance(data, list)

        status_map = {item['status']: item for item in data}
        assert status_map['在库']['count'] == 2
        assert status_map['使用中']['count'] == 1
        assert status_map['报废']['count'] == 1

        # Verify percentage for 在库: 2/4 * 100 = 50.0
        assert status_map['在库']['percentage'] == 50.0


# ---------------------------------------------------------------------------
# Transfers report
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportTransfers:
    """GET /api/reports/transfers/ — transfer data and filters."""

    def _create_transfer(self, branch, **overrides):
        defaults = dict(
            调拨日期=date(2026, 4, 10),
            资产编号='TR-RPT-001',
            资产名称='报表调拨资产',
            调出分公司=branch.name,
            调入分公司=branch.name,
            调拨数量=1,
            action_type='purchase',
            审批状态='已通过',
            from_branch=branch,
            to_branch=branch,
        )
        defaults.update(overrides)
        return Transfer.objects.create(**defaults)

    def test_transfers_report_returns_data(self, authenticated_client, branch):
        self._create_transfer(branch)
        resp = authenticated_client.get('/api/reports/transfers/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert isinstance(data, list)
        assert len(data) >= 1
        item = data[0]
        assert 'id' in item
        assert 'date' in item
        assert 'assetCode' in item
        assert 'assetName' in item
        assert 'fromBranch' in item
        assert 'toBranch' in item
        assert 'quantity' in item
        assert 'status' in item
        assert 'actionType' in item

    def test_filter_by_approval_status(self, authenticated_client, branch):
        self._create_transfer(branch, 审批状态='已通过')
        self._create_transfer(
            branch, 资产编号='TR-RPT-002', 审批状态='待审批',
        )

        resp = authenticated_client.get('/api/reports/transfers/?status=已通过')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert all(item['status'] == '已通过' for item in data)

    def test_filter_by_action_type(self, authenticated_client, branch):
        self._create_transfer(branch, action_type='purchase')
        self._create_transfer(
            branch, 资产编号='TR-RPT-003', action_type='transfer',
        )

        resp = authenticated_client.get('/api/reports/transfers/?type=purchase')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert all(item['actionType'] == 'purchase' for item in data)


# ---------------------------------------------------------------------------
# Data scoping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportDataScoping:
    """Role-based data scoping: admin sees all, supervisor sees region, staff sees branch."""

    def test_admin_sees_all_assets_in_overview(self, admin_user, make_asset, make_asset_b):
        make_asset(当前状态='在库')
        make_asset_b(当前状态='在库')

        client = _client_for(admin_user)
        resp = client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['totalAssets'] == 2

    def test_supervisor_sees_only_own_region(self, supervisor_user, make_asset, make_asset_b):
        # supervisor_user is in region fixture (测试区域)
        make_asset(当前状态='在库')
        make_asset_b(当前状态='在库')  # second region

        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['totalAssets'] == 1

    def test_staff_sees_only_own_branch(self, staff_user, make_asset, make_asset_b):
        # staff_user is in branch fixture (测试分公司)
        make_asset(当前状态='在库')
        make_asset(当前状态='使用中')
        make_asset_b(当前状态='在库')  # different branch

        client = _client_for(staff_user)
        resp = client.get('/api/reports/overview/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['totalAssets'] == 2

    def test_supervisor_by_branch_excludes_other_region(
        self, supervisor_user, branch, second_branch,
    ):
        Asset.objects.create(
            序号=1, 分公司=branch.name, 分公司编号=branch.code,
            资产编号='SCO-001', 资产类目='固定资产', 物品分类='办公设备',
            资产名称='Region Asset', 数量=1, 当前状态='在库', branch=branch,
        )
        Asset.objects.create(
            序号=2, 分公司=second_branch.name, 分公司编号=second_branch.code,
            资产编号='SCO-002', 资产类目='固定资产', 物品分类='办公设备',
            资产名称='Other Region Asset', 数量=1, 当前状态='在库', branch=second_branch,
        )

        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/by-branch/')
        assert resp.status_code == status.HTTP_200_OK
        names = [item['name'] for item in resp.data]
        assert branch.name in names
        assert second_branch.name not in names

    def test_staff_transfers_only_own_branch(self, staff_user, branch, second_branch):
        Transfer.objects.create(
            调拨日期=date(2026, 4, 10),
            资产编号='SCO-T-001', 资产名称='Scoped Transfer',
            调出分公司=branch.name, 调入分公司=branch.name,
            调拨数量=1, action_type='purchase', 审批状态='已通过',
            from_branch=branch, to_branch=branch,
        )
        Transfer.objects.create(
            调拨日期=date(2026, 4, 11),
            资产编号='SCO-T-002', 资产名称='Other Transfer',
            调出分公司=second_branch.name, 调入分公司=second_branch.name,
            调拨数量=1, action_type='purchase', 审批状态='已通过',
            from_branch=second_branch, to_branch=second_branch,
        )

        client = _client_for(staff_user)
        resp = client.get('/api/reports/transfers/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]['assetCode'] == 'SCO-T-001'
