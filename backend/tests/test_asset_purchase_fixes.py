"""资产编辑(PATCH) / 采购草稿 / 采购审批入库联动 修复测试。"""
import pytest
from conftest import _client_for


def _action_url(action, pk=None):
    return f'/api/transfers/{pk}/{action}' if pk else f'/api/transfers/{action}'


def _item_uuid(code):
    from apps.categories.models import Category
    return str(Category.objects.get(asset_code=code).id)


@pytest.mark.django_db
class TestPurchaseApproveStock:
    """P1：采购审批通过写台账（在库+N），不再创建/累加 Asset。"""

    def _create_purchase(self, client, branch, code):
        resp = client.post(_action_url('purchase'), {
            '调拨日期': '2026-07-14', '调拨原因': '采购', '调出分公司': branch.name,
            'items': [{'item': _item_uuid(code), '数量': 5}],
        }, format='json')
        assert resp.status_code == 201
        return resp.data['id']

    def test_approve_creates_ledger_row(self, admin_user, branch):
        from apps.assets.models import AssetStock
        client = _client_for(admin_user)
        tid = self._create_purchase(client, branch, 'APR-001')
        resp = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '已入库'
        row = AssetStock.objects.get(branch=branch, item__asset_code='APR-001')
        assert row.在库数量 == 5

    def test_approve_increments_existing_row(self, admin_user, branch):
        from apps.assets.models import AssetStock
        from apps.assets.services import ledger
        from apps.categories.models import Category
        item = Category.objects.get(asset_code='APR-002')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 3, '测试造数')
        client = _client_for(admin_user)
        tid = self._create_purchase(client, branch, 'APR-002')
        resp = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == 200
        assert AssetStock.objects.get(branch=branch, item=item).在库数量 == 8  # 3 + 5



class TestPurchaseDraft:
    def test_create_draft(self, admin_user, branch):
        from apps.transfers.models import Transfer
        client = _client_for(admin_user)
        resp = client.post(_action_url('purchase'), {
            '调拨日期': '2026-07-14', '调出分公司': branch.name,
            'items': [{'item': _item_uuid('DRF-001'), '数量': 1}], 'draft': True,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '草稿'
        transfer = Transfer.objects.get(pk=resp.data['id'])
        assert transfer.审批状态 == '草稿'
        assert transfer.lines.get().item.asset_code == 'DRF-001'

    def test_submit_draft(self, admin_user, branch):
        client = _client_for(admin_user)
        resp = client.post(_action_url('purchase'), {
            '调拨日期': '2026-07-14', '调出分公司': branch.name,
            'items': [{'item': _item_uuid('DRF-002'), '数量': 1}], 'draft': True,
        }, format='json')
        tid = resp.data['id']
        resp2 = client.post(f'/api/transfers/{tid}/submit', format='json')
        assert resp2.status_code == 200
        assert resp2.data['审批状态'] == '待审批'
