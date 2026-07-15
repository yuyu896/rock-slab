"""分公司筛选测试：资产/固定资产按分公司名称筛选命中（即便分公司编号不一致），流转按名称筛选/创建回填。"""
import pytest
from datetime import date
from conftest import _client_for


def _make_asset(branch, code, name='测试资产'):
    from apps.assets.models import Asset
    return Asset.objects.create(
        序号=1, 分公司=branch.name, 分公司编号='WRONG-CODE',  # 故意与真实 code 不一致，证明按名称过滤
        资产编号=code, 资产类目='固定', 物品分类='办公',
        资产名称=name, 数量=1, branch=branch,
    )


@pytest.mark.django_db
class TestBranchFilter:
    def test_asset_filter_by_branch_name(self, admin_user, branch, second_branch):
        _make_asset(branch, 'BF-A1')
        _make_asset(second_branch, 'BF-A2')
        client = _client_for(admin_user)
        resp = client.get('/api/assets/', {'branch': branch.name})
        assert resp.status_code == 200
        codes = [a['资产编号'] for a in resp.data['results']]
        assert 'BF-A1' in codes
        assert 'BF-A2' not in codes

    def test_fixed_asset_filter_by_branch_name(self, admin_user, branch, second_branch):
        from apps.assets.models import FixedAsset
        p1 = _make_asset(branch, 'BF-FA-P1')
        p2 = _make_asset(second_branch, 'BF-FA-P2')
        FixedAsset.objects.create(asset=p1, 内部编号='BF-FA-P1-1', 资产编号='BF-FA-P1',
                                  资产名称='X', 分公司=branch.name, 分公司编号='WRONG-CODE', branch=branch)
        FixedAsset.objects.create(asset=p2, 内部编号='BF-FA-P2-1', 资产编号='BF-FA-P2',
                                  资产名称='Y', 分公司=second_branch.name, 分公司编号='WRONG-CODE', branch=second_branch)
        client = _client_for(admin_user)
        resp = client.get('/api/assets/fixed-assets', {'branch': branch.name})
        assert resp.status_code == 200
        codes = [f['资产编号'] for f in resp.data['results']]
        assert 'BF-FA-P1' in codes
        assert 'BF-FA-P2' not in codes

    def test_transfer_filter_by_from_branch_name(self, admin_user, branch, second_branch):
        from apps.transfers.models import Transfer
        Transfer.objects.create(调拨日期=date(2026, 7, 10), action_type='transfer',
                                调出分公司=branch.name, 资产编号='BF-T1', 资产名称='X', 调拨数量=1)
        Transfer.objects.create(调拨日期=date(2026, 7, 10), action_type='transfer',
                                调出分公司=second_branch.name, 资产编号='BF-T2', 资产名称='Y', 调拨数量=1)
        client = _client_for(admin_user)
        resp = client.get('/api/transfers/', {'fromBranch': branch.name})
        assert resp.status_code == 200
        codes = [t['资产编号'] for t in resp.data['results']]
        assert 'BF-T1' in codes
        assert 'BF-T2' not in codes

    def test_transfer_create_backfills_branch_name(self, admin_user, branch, second_branch):
        from apps.transfers.models import Transfer
        client = _client_for(admin_user)
        # 表单只传分公司外键 id（fromBranch/toBranch），不传调出/调入分公司名称
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-07-10',
            '资产编号': 'BF-C1',
            '资产名称': 'X',
            '调拨数量': 1,
            'fromBranch': str(branch.id),
            'toBranch': str(second_branch.id),
        }, format='json')
        assert resp.status_code == 201
        t = Transfer.objects.get(资产编号='BF-C1')
        assert t.调出分公司 == branch.name   # 由 from_branch 回填
        assert t.调入分公司 == second_branch.name
