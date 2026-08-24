"""批量删除（资产 / 固定资产）测试。"""
import pytest
from conftest import _client_for


def _make_asset(branch, code, name='测试资产'):
    from apps.assets.models import Asset
    return Asset.objects.create(
        序号=1, 分公司=branch.name, 分公司编号=branch.code,
        资产编号=code, 资产类目='固定', 物品分类='办公',
        资产名称=name, 数量=1, branch=branch,
    )


@pytest.mark.django_db
class TestAssetBatchDelete:
    """P1 冻结：资产批量删除 405（固定资产批量删除不受影响）。"""

    def test_batch_delete_returns_405(self, admin_user, make_asset):
        from conftest import _client_for
        asset = make_asset()
        client = _client_for(admin_user)
        resp = client.post('/api/assets/batch-delete', {'ids': [str(asset.id)]}, format='json')
        assert resp.status_code == 405



class TestFixedAssetBatchDelete:
    def test_admin_batch_delete(self, admin_user, branch):
        """P2 第二刀：实例批量删除冻结——档案永不物理删除，退出走回收退役。"""
        from apps.categories.models import Category
        from apps.assets.models import FixedAsset
        item = Category.objects.create(
            asset_category='固定', item_category='办公',
            asset_name='实例品目', asset_code='BD-FA-P', unit='台',
            management_type='instance',
        )
        f1 = FixedAsset.objects.create(
            item=item, 内部编号='BD-FA-P-1', 当前状态='在库', branch=branch)
        f2 = FixedAsset.objects.create(
            item=item, 内部编号='BD-FA-P-2', 当前状态='在库', branch=branch)
        client = _client_for(admin_user)
        resp = client.post('/api/assets/fixed-assets/batch-delete',
                           {'ids': [str(f1.id), str(f2.id)]}, format='json')
        assert resp.status_code == 405
        assert FixedAsset.objects.filter(id__in=[f1.id, f2.id]).count() == 2
