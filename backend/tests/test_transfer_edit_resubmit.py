"""流转编辑(仅已驳回) + 重新提交 测试。"""
import pytest
from conftest import _client_for


def _action_url(action, pk=None):
    return f'/api/transfers/{pk}/{action}' if pk else f'/api/transfers/{action}'


def _make_transfer(client, code, branch, item_id, status=None):
    payload = {
        '调拨日期': '2026-07-14', '调出分公司': branch.name,
        'items': [{'item': item_id(code), '数量': 1}],
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
    def test_update_rejected_succeeds(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-001', branch, item_id, status='已驳回')
        resp = client.patch(f'/api/transfers/{t.id}', {
            'items': [{'item': item_id('EDT-001'), '数量': 9}],
            '备注': '修正',
        }, format='json')
        assert resp.status_code == 200
        t.refresh_from_db()
        line = t.lines.get(行号=1)
        assert line.数量 == 9
        assert line.item.asset_code == 'EDT-001'
        assert t.lines.count() == 1
        assert t.备注 == '修正'

    def test_update_non_rejected_rejected(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-002', branch, item_id, status='待审批')
        resp = client.patch(f'/api/transfers/{t.id}', {
            'items': [{'item': item_id('EDT-002'), '数量': 9}],
        }, format='json')
        assert resp.status_code == 400

    def test_resubmit_rejected(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-003', branch, item_id, status='已驳回')
        resp = client.post(f'/api/transfers/{t.id}/resubmit', format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '待审批'

    def test_resubmit_non_rejected_rejected(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_transfer(client, 'EDT-004', branch, item_id, status='待审批')
        resp = client.post(f'/api/transfers/{t.id}/resubmit', format='json')
        assert resp.status_code == 400
