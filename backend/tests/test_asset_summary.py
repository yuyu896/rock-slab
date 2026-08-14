"""
Tests for asset summary: GET /api/assets/summary — per-branch asset code aggregation with data scoping.
"""
import pytest
from rest_framework import status

from apps.assets.models import Asset
from conftest import _client_for


def _create_asset(seq, branch_obj, code, name):
    return Asset.objects.create(
        序号=seq, 分公司=branch_obj.name, 分公司编号=branch_obj.code,
        资产编号=code, 资产类目='固定资产', 物品分类='办公设备',
        资产名称=name, 数量=1, 当前状态='在库', branch=branch_obj,
    )


@pytest.mark.django_db
class TestAssetSummary:
    """GET /api/assets/summary — branchName/branchCode/total/minCode/maxCode."""

    def test_summary_admin_sees_all_branches(self, authenticated_client, branch, second_branch):
        _create_asset(1, branch, 'CS001-003', '资产一')
        _create_asset(2, branch, 'CS001-001', '资产二')
        _create_asset(3, second_branch, 'RG2001-005', '资产三')

        resp = authenticated_client.get('/api/assets/summary')
        assert resp.status_code == status.HTTP_200_OK
        rows = resp.data
        assert [r['branchCode'] for r in rows] == ['CS001', 'RG2001']
        first = rows[0]
        assert first['branchName'] == branch.name
        assert first['total'] == 2
        assert first['minCode'] == 'CS001-001'
        assert first['maxCode'] == 'CS001-003'
        assert rows[1]['total'] == 1

    def test_summary_scoped_to_authorized_branches(
        self, supervisor_user, branch, second_branch,
    ):
        _create_asset(1, branch, 'CS001-001', '本区资产')
        _create_asset(2, second_branch, 'RG2001-001', '他区资产')

        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/summary')
        assert resp.status_code == status.HTTP_200_OK
        codes = [r['branchCode'] for r in resp.data]
        assert codes == [branch.code]
        assert resp.data[0]['total'] == 1

    def test_summary_no_grant_returns_empty(self, db, branch):
        from apps.users.models import User
        _create_asset(1, branch, 'CS001-001', '资产')

        user = User.objects.create_user(
            phone='13911112222', name='无授权用户', password='test123456',
            role='staff', status='active', branch=branch,
        )
        client = _client_for(user)
        resp = client.get('/api/assets/summary')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []

    def test_summary_unauthenticated(self, api_client):
        resp = api_client.get('/api/assets/summary')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
