"""流转编辑(仅已驳回) + 重新提交 测试。"""
import pytest
from conftest import _client_for


def _action_url(action, pk=None):
    return f'/api/transfers/{pk}/{action}' if pk else f'/api/transfers/{action}'


def _make_transfer(client, code, status=None):
    payload = {
        '调拨日期': '2026-07-14', '资产编号': code, '资产名称': '编辑测试',
        '调拨数量': 1, '调出分公司': '测试分公司',
    }
    resp = client.post(_action_url('purchase'), payload, format='json')
    assert resp.status_code == 201
    from apps.transfers.models import Transfer
    t = Transfer.objects.get(id=resp.data['id'])
    if status:
        t.审批状态 = status
        t.save(update_fields=['审批状态'])
    return t


@pytest.mark.django_db
class TestTransferEditResubmit:
    def test_update_rejected_succeeds(self, admin_user):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-001', status='已驳回')
        resp = client.patch(f'/api/transfers/{t.id}', {'调拨数量': 9, '备注': '修正'}, format='json')
        assert resp.status_code == 200
        t.refresh_from_db()
        assert t.调拨数量 == 9
        assert t.备注 == '修正'

    def test_update_non_rejected_rejected(self, admin_user):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-002', status='待审批')
        resp = client.patch(f'/api/transfers/{t.id}', {'调拨数量': 9}, format='json')
        assert resp.status_code == 400

    def test_resubmit_rejected(self, admin_user):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-003', status='已驳回')
        resp = client.post(f'/api/transfers/{t.id}/resubmit', format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '待审批'

    def test_resubmit_non_rejected_rejected(self, admin_user):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-004', status='待审批')
        resp = client.post(f'/api/transfers/{t.id}/resubmit', format='json')
        assert resp.status_code == 400
