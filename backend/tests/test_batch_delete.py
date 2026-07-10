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
    def test_admin_batch_delete(self, admin_user, branch):
        from apps.assets.models import Asset
        a1 = _make_asset(branch, 'BD-A01')
        a2 = _make_asset(branch, 'BD-A02')
        a3 = _make_asset(branch, 'BD-A03')
        client = _client_for(admin_user)
        resp = client.post('/api/assets/batch-delete',
                           {'ids': [str(a1.id), str(a2.id)]}, format='json')
        assert resp.status_code == 200
        assert resp.data['deleted'] == 2
        assert not Asset.objects.filter(id__in=[a1.id, a2.id]).exists()
        assert Asset.objects.filter(id=a3.id).exists()

    def test_staff_forbidden(self, staff_user, branch):
        from apps.assets.models import Asset
        a1 = _make_asset(branch, 'BD-S01')
        client = _client_for(staff_user)
        resp = client.post('/api/assets/batch-delete', {'ids': [str(a1.id)]}, format='json')
        assert resp.status_code == 403
        assert Asset.objects.filter(id=a1.id).exists()  # 未被删除

    def test_empty_ids_bad_request(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post('/api/assets/batch-delete', {'ids': []}, format='json')
        assert resp.status_code == 400

    def test_respects_data_scope(self, supervisor_user, branch, second_branch):
        # supervisor 范围为 region（含 branch，不含 second_branch）
        from apps.assets.models import Asset
        in_scope = _make_asset(branch, 'BD-SC-IN')
        out_of_scope = _make_asset(second_branch, 'BD-SC-OUT')
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/batch-delete',
                           {'ids': [str(in_scope.id), str(out_of_scope.id)]}, format='json')
        assert resp.status_code == 200
        assert resp.data['deleted'] == 1  # 仅范围内的被删
        assert not Asset.objects.filter(id=in_scope.id).exists()
        assert Asset.objects.filter(id=out_of_scope.id).exists()


@pytest.mark.django_db
class TestFixedAssetBatchDelete:
    def test_admin_batch_delete(self, admin_user, branch):
        from apps.assets.models import Asset, FixedAsset
        parent = Asset.objects.create(
            序号=1, 分公司=branch.name, 分公司编号=branch.code,
            资产编号='BD-FA-P', 资产类目='固定', 物品分类='办公',
            资产名称='父资产', 数量=0, branch=branch,
        )
        f1 = FixedAsset.objects.create(asset=parent, 内部编号='BD-FA-P-1',
                                       资产编号='BD-FA-P', 资产名称='实例1')
        f2 = FixedAsset.objects.create(asset=parent, 内部编号='BD-FA-P-2',
                                       资产编号='BD-FA-P', 资产名称='实例2')
        client = _client_for(admin_user)
        resp = client.post('/api/assets/fixed-assets/batch-delete',
                           {'ids': [str(f1.id), str(f2.id)]}, format='json')
        assert resp.status_code == 200
        assert resp.data['deleted'] == 2
        assert FixedAsset.objects.filter(id__in=[f1.id, f2.id]).count() == 0
