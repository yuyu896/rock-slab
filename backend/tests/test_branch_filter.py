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


def _make_transfer(item_code, branch_name):
    """单头 + 一条明细行（P2 契约）：品目身份在字典，数量在明细行。"""
    from apps.categories.models import Category
    from apps.transfers.models import Transfer, TransferLine
    item, _ = Category.objects.get_or_create(
        asset_code=item_code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {item_code}', 'unit': '个',
        },
    )
    t = Transfer.objects.create(
        调拨日期=date(2026, 7, 10), action_type='transfer', 调出分公司=branch_name,
    )
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=1)
    return t


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
        from apps.categories.models import Category
        item = Category.objects.create(
            asset_category='固定', item_category='办公',
            asset_name='BF实例品目', asset_code='BF-FA-P1', unit='台',
            management_type='instance',
        )
        FixedAsset.objects.create(item=item, 内部编号='BF-FA-P1-1',
                                  当前状态='在库', branch=branch)
        FixedAsset.objects.create(item=item, 内部编号='BF-FA-P1-2',
                                  当前状态='在库', branch=second_branch)
        client = _client_for(admin_user)
        resp = client.get('/api/assets/fixed-assets', {'branch': branch.name})
        assert resp.status_code == 200
        codes = [f['item_code'] for f in resp.data['results']]
        assert 'BF-FA-P1' in codes
        inner = [f['内部编号'] for f in resp.data['results']]
        assert 'BF-FA-P1-1' in inner
        assert 'BF-FA-P1-2' not in inner

    def test_transfer_filter_by_from_branch_name(self, admin_user, branch, second_branch):
        _make_transfer('BF-T1', branch.name)
        _make_transfer('BF-T2', second_branch.name)
        client = _client_for(admin_user)
        resp = client.get('/api/transfers/', {'fromBranch': branch.name})
        assert resp.status_code == 200
        codes = [line['item_code'] for t in resp.data['results'] for line in t['lines']]
        assert 'BF-T1' in codes
        assert 'BF-T2' not in codes

    def test_transfer_create_backfills_branch_name(self, admin_user, branch, second_branch, item_id):
        from apps.transfers.models import Transfer
        client = _client_for(admin_user)
        # 表单只传分公司外键 id（fromBranch/toBranch）；调出分公司名称仅用于通过必填校验，
        # 调入分公司名称留空以验证由 toBranch 外键回填
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-07-10',
            '调出分公司': branch.name,
            'fromBranch': str(branch.id),
            'toBranch': str(second_branch.id),
            'items': [{'item': item_id('BF-C1'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201
        t = Transfer.objects.get(lines__item__asset_code='BF-C1')
        assert t.调出分公司 == branch.name   # 由 from_branch 回填
        assert t.调入分公司 == second_branch.name
