"""批量删除（固定资产实例）测试；Asset 段已随 P2 第三刀退役。"""
import pytest
from conftest import _client_for


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
