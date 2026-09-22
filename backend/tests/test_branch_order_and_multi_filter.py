"""分公司排序/多选筛选 + 流转列表统一排序（branch-order-and-multi-filter）。"""
import pytest
from conftest import _client_for


def _mk(action, date_str, status, to_branch, name=None):
    from apps.transfers.models import Transfer
    return Transfer.objects.create(
        action_type=action,
        调拨日期=date_str,
        调入分公司=name or to_branch.name,
        to_branch=to_branch,
        审批状态=status,
    )


@pytest.mark.django_db
class TestTransferListOrdering:
    def test_status_rank_then_date_desc(self, admin_user, branch, second_branch):
        _mk('purchase', '2026-09-01', '已入库', branch)
        _mk('purchase', '2026-09-10', '待审批', second_branch)
        _mk('purchase', '2026-09-05', '草稿', branch)
        _mk('purchase', '2026-09-20', '待审批', branch)
        _mk('purchase', '2026-09-08', '已入库', branch)

        resp = _client_for(admin_user).get('/api/transfers/', {'type': 'purchase', 'pageSize': 50})
        assert resp.status_code == 200
        got = [(t['审批状态'], t['调拨日期']) for t in resp.data['results']]
        assert got == [
            ('待审批', '2026-09-20'),  # 状态置顶，组内日期倒序
            ('待审批', '2026-09-10'),
            ('草稿', '2026-09-05'),
            ('已入库', '2026-09-08'),
            ('已入库', '2026-09-01'),
        ]

    def test_pending_first_across_pagination(self, admin_user, branch):
        for i in range(3):
            _mk('purchase', f'2026-09-{i+1:02d}', '已入库', branch)
        _mk('purchase', '2026-09-10', '待审批', branch)

        resp = _client_for(admin_user).get('/api/transfers/', {'type': 'purchase', 'pageSize': 3})
        assert resp.data['results'][0]['审批状态'] == '待审批'  # 置顶跨页一致（首页头部）


@pytest.mark.django_db
class TestBranchMultiFilter:
    def test_to_branch_multi_union(self, admin_user, branch, second_branch):
        from apps.organizations.models import Branch
        third = Branch.objects.create(name='第三分公司', code='TH001', team=branch.team, status='active')
        _mk('purchase', '2026-09-01', '待审批', branch)
        _mk('purchase', '2026-09-02', '待审批', second_branch)
        _mk('purchase', '2026-09-03', '待审批', third)

        resp = _client_for(admin_user).get(
            '/api/transfers/', {'type': 'purchase', 'toBranch': f'{branch.name},{second_branch.name}'})
        names = {t['调入分公司'] for t in resp.data['results']}
        assert names == {branch.name, second_branch.name}  # 并集命中两家，第三家排除

    def test_empty_means_all(self, admin_user, branch, second_branch):
        _mk('purchase', '2026-09-01', '待审批', branch)
        _mk('purchase', '2026-09-02', '待审批', second_branch)
        resp = _client_for(admin_user).get('/api/transfers/', {'type': 'purchase', 'toBranch': ''})
        assert resp.data['count'] == 2

    def test_stock_branch_multi(self, admin_user, branch, second_branch, item_id):
        from apps.assets.services import ledger
        from apps.categories.models import Category
        cat = Category.objects.get(asset_code='PUR-001')
        ledger.apply_adjustment(branch, cat, ledger.COLUMN_STOCK, 3, '多选测试')
        ledger.apply_adjustment(second_branch, cat, ledger.COLUMN_STOCK, 5, '多选测试')

        resp = _client_for(admin_user).get(
            '/api/assets/summary', {'branch': f'{branch.name},{second_branch.name}'})
        assert resp.status_code == 200
        got_branches = {row['branch_name'] for row in resp.data['results']}
        assert got_branches == {branch.name, second_branch.name}
