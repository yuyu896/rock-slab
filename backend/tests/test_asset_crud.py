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


@pytest.mark.django_db
class TestAssetCreateValidation:
    """资产（品目）创建：序号自增 + 按分公司名称回填 + 资产编号须在分类登记。"""

    def _payload(self, category, **overrides):
        data = {
            '资产编号': category.asset_code,
            '资产类目': category.asset_category,
            '物品分类': category.item_category,
            '资产名称': '新建资产',
            '数量': 2,
        }
        data.update(overrides)
        return data

    def test_create_auto_increments_序号(self, supervisor_user, make_asset, category):
        make_asset()  # 既有资产，序号=1
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/', self._payload(category))
        assert resp.status_code == 201
        assert resp.data['序号'] == 2  # 最大序号 + 1

    def test_create_序号_first_record(self, supervisor_user, category):
        """空表创建时序号取 1。"""
        from apps.assets.models import Asset
        Asset.objects.all().delete()
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/', self._payload(category))
        assert resp.status_code == 201
        assert resp.data['序号'] == 1

    def test_create_explicit_序号_preserved(self, supervisor_user, category):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/', self._payload(category, 序号=88))
        assert resp.status_code == 201
        assert resp.data['序号'] == 88

    def test_create_resolves_branch_by_name(self, supervisor_user, branch, category):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/', self._payload(category, 分公司=branch.name))
        assert resp.status_code == 201
        from apps.assets.models import Asset
        asset = Asset.objects.get(资产编号=category.asset_code)
        assert asset.branch_id == branch.id
        assert asset.分公司编号 == branch.code
        assert asset.分公司 == branch.name

    def test_create_unknown_branch_name_still_created(self, supervisor_user, branch, category):
        """分公司名称解析不到时不阻断创建（branch 置空）。"""
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/', self._payload(category, 分公司='不存在的分公司'))
        assert resp.status_code == 201
        from apps.assets.models import Asset
        asset = Asset.objects.get(资产编号=category.asset_code)
        assert asset.branch_id is None

    def test_create_unregistered_asset_code_rejected(self, supervisor_user, category):
        """资产编号未在资产分类登记时拒绝创建，返回 400。"""
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/', self._payload(category, 资产编号='UNREGISTERED-999'))
        assert resp.status_code == 400
        assert '资产编号' in resp.data
        assert '资产分类' in str(resp.data['资产编号'])
