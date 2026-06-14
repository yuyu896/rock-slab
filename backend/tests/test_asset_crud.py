"""
Tests for asset CRUD permissions (add-asset-crud-permissions).
"""
import pytest
from conftest import _client_for


@pytest.mark.django_db
class TestAssetUpdatePermissions:
    def test_supervisor_update_own_region(self, supervisor_user, make_asset):
        asset = make_asset()
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/assets/{asset.id}', {'资产名称': '已修改'})
        assert resp.status_code == 200
        asset.refresh_from_db()
        assert asset.资产名称 == '已修改'

    def test_supervisor_update_other_region_404(self, supervisor_user, make_asset_b):
        asset_b = make_asset_b()
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/assets/{asset_b.id}', {'资产名称': '尝试修改'})
        assert resp.status_code == 404

    def test_leader_update_forbidden(self, leader_user, make_asset):
        asset = make_asset()
        client = _client_for(leader_user)
        resp = client.patch(f'/api/assets/{asset.id}', {'资产名称': '尝试修改'})
        assert resp.status_code == 403


@pytest.mark.django_db
class TestAssetDeletePermissions:
    def test_supervisor_delete_own_region(self, supervisor_user, make_asset):
        from apps.assets.models import Asset
        asset = make_asset()
        client = _client_for(supervisor_user)
        resp = client.delete(f'/api/assets/{asset.id}')
        assert resp.status_code == 204
        assert not Asset.objects.filter(id=asset.id).exists()

    def test_staff_delete_forbidden(self, staff_user, make_asset):
        asset = make_asset()
        client = _client_for(staff_user)
        resp = client.delete(f'/api/assets/{asset.id}')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestAssetBranchSync:
    def test_branch_change_syncs_denormalized_fields(self, supervisor_user, make_asset):
        from apps.organizations.models import Branch
        asset = make_asset()
        branch_a2 = Branch.objects.create(
            name='分公司A2', code='TSA02', region=supervisor_user.region, status='active',
        )
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/assets/{asset.id}', {'branch': branch_a2.id})
        assert resp.status_code == 200
        asset.refresh_from_db()
        assert asset.分公司 == '分公司A2'
        assert asset.分公司编号 == 'TSA02'
