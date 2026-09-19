"""采购单撤回（待审批→草稿，仅创建人）+ 草稿可编辑 测试。"""
import pytest
from conftest import _client_for


def _make_purchase(client, code, branch, item_id, status=None, draft=False):
    payload = {
        '调拨日期': '2026-09-19', '调出分公司': branch.name,
        'items': [{'item': item_id(code), '数量': 2, '供应商': '甲供应商'}],
    }
    if draft:
        payload['draft'] = True
    resp = client.post('/api/transfers/purchase', payload, format='json')
    assert resp.status_code == 201
    from apps.transfers.models import Transfer
    t = Transfer.objects.get(id=resp.data['id'])
    if status:
        t.审批状态 = status
        t.save(update_fields=['审批状态'])
    return t


@pytest.mark.django_db
class TestPurchaseWithdraw:
    def test_creator_withdraws_pending(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_purchase(client, 'PUR-001', branch, item_id, status='待审批')
        resp = client.post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '草稿'
        t.refresh_from_db()
        assert t.审批状态 == '草稿'

    def test_non_creator_rejected(self, admin_user, branch, item_id, db):
        from django.contrib.auth import get_user_model
        other_admin = get_user_model().objects.create_user(
            phone='13900000009', name='二号管理员', password='test123456',
            role='admin', status='active',
        )
        t = _make_purchase(_client_for(admin_user), 'APR-001', branch, item_id, status='待审批')
        resp = _client_for(other_admin).post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 400
        t.refresh_from_db()
        assert t.审批状态 == '待审批'

    @pytest.mark.parametrize('status', ['草稿', '已通过', '已驳回', '已入库'])
    def test_non_pending_status_rejected(self, admin_user, branch, item_id, status):
        client = _client_for(admin_user)
        t = _make_purchase(client, 'APR-002', branch, item_id, status=status)
        resp = client.post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 400

    def test_withdraw_then_edit_then_submit_full_chain(self, admin_user, branch, item_id):
        from apps.assets.models import AssetStock
        client = _client_for(admin_user)
        t = _make_purchase(client, 'APR-003', branch, item_id, status='待审批')
        stock_before = list(AssetStock.objects.values('id', '在库数量'))

        assert client.post(f'/api/transfers/{t.id}/withdraw', format='json').status_code == 200
        t.refresh_from_db()
        assert t.审批状态 == '草稿'

        # 草稿可编辑：改数量与行级供应商
        resp = client.patch(f'/api/transfers/{t.id}', {
            'items': [{'item': item_id('APR-003'), '数量': 5, '供应商': '乙供应商'}],
        }, format='json')
        assert resp.status_code == 200
        line = t.lines.get(行号=1)
        assert line.数量 == 5
        assert line.供应商 == '乙供应商'

        # 草稿重新提交进入审批流
        resp = client.post(f'/api/transfers/{t.id}/submit', format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '待审批'

        # 全程未触碰台账
        assert list(AssetStock.objects.values('id', '在库数量')) == stock_before

    def test_draft_directly_editable(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_purchase(client, 'PUR-sup', branch, item_id, draft=True)
        assert t.审批状态 == '草稿'
        resp = client.patch(f'/api/transfers/{t.id}', {
            'items': [{'item': item_id('PUR-sup'), '数量': 3, '供应商': '丙供应商'}],
        }, format='json')
        assert resp.status_code == 200
        t.refresh_from_db()
        assert t.lines.get(行号=1).数量 == 3
