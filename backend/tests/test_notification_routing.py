"""notification-routing-accuracy：业务分公司路由/空分公司不广播/已入库识别/created_by 定位。"""
import pytest
from rest_framework import status

from apps.notifications.models import Notification


def _user(phone, name, role='manager', branch=None, scope_branch=None, scope_all=False, ops=()):
    from django.contrib.auth import get_user_model
    from apps.permissions.models import ManagementScope, OperationGrant
    u = get_user_model().objects.create_user(
        phone=phone, name=name, password='test123456',
        role=role, status='active', branch=branch,
    )
    if scope_all:
        ManagementScope.objects.create(user=u, is_all_data=True)
    elif scope_branch is not None:
        ManagementScope.objects.create(user=u, branch=scope_branch)
    for code in ops:
        OperationGrant.objects.create(user=u, code=code)
    return u


def _client(u):
    from conftest import _client_for
    return _client_for(u)


def _ledger_item(code):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={'asset_category': '路由测试', 'item_category': '办公',
                  'asset_name': f'品目 {code}', 'unit': '台', 'management_type': 'ledger'},
    )
    return item


def _web_purchase(client, item, branch):
    """Web 端语义：只传入调分公司（调出侧为空）。"""
    resp = client.post('/api/transfers/purchase', {
        '调拨日期': '2026-09-30', '调入分公司': branch.name,
        'items': [{'item': str(item.id), '数量': 2}],
    }, format='json')
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return resp.data['id']


@pytest.mark.django_db
class TestPurchaseRouting:
    def test_web_purchase_no_broadcast(self, branch, second_branch):
        item = _ledger_item('NR-1')
        m_a = _user('13944000001', 'A司经理', scope_branch=branch, ops=('approve_transfer',))
        m_b = _user('13944000002', 'B司经理', scope_branch=second_branch, ops=('approve_transfer',))
        m_h = _user('13944000003', '总部经理', scope_all=True, ops=('approve_transfer',))
        creator = _user('13944000004', '采购组长', role='leader', branch=branch, scope_branch=branch)

        _web_purchase(_client(creator), item, branch)

        def _pending(u):
            return Notification.objects.filter(recipient=u, notification_type='approval').count()

        assert _pending(m_a) == 1            # 调入方审批人收到
        assert _pending(m_b) == 0            # 无关分公司不广播
        assert _pending(m_h) == 1            # 全量授权天然覆盖
        assert _pending(creator) == 0

    def test_purchase_approved_notifies_creator_and_cc(self, branch):
        from apps.notifications.models import ApprovalCC
        item = _ledger_item('NR-2')
        m_a = _user('13944000011', 'A司经理', scope_branch=branch, ops=('approve_transfer',))
        cc_u = _user('13944000012', '抄送经理', scope_branch=branch, ops=('view_all_notifications',))
        creator = _user('13944000013', '采购组长', role='leader', branch=branch, scope_branch=branch)

        tid = _web_purchase(_client(creator), item, branch)
        resp = _client(m_a).post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == status.HTTP_200_OK

        # 采购落「已入库」：创建人经 created_by 收到结果通知，抄送照常
        assert Notification.objects.filter(
            recipient=creator, notification_type='task', title__contains='审批通过',
        ).count() == 1
        assert ApprovalCC.objects.filter(transfer_id=tid, recipient=cc_u).count() == 1

    def test_same_name_not_misnotified(self, branch):
        item = _ledger_item('NR-3')
        m_a = _user('13944000021', 'A司经理', scope_branch=branch, ops=('approve_transfer',))
        creator = _user('13944000022', '王小明', role='leader', branch=branch, scope_branch=branch)
        namesake = _user('13944000023', '王小明', role='leader', branch=branch)  # 重名他人

        tid = _web_purchase(_client(creator), item, branch)
        _client(m_a).post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')

        assert Notification.objects.filter(recipient=creator, title__contains='审批通过').count() == 1
        assert Notification.objects.filter(recipient=namesake, title__contains='审批').count() == 0

    def test_purchase_rejected_notifies_creator(self, branch):
        item = _ledger_item('NR-4')
        m_a = _user('13944000031', 'A司经理', scope_branch=branch, ops=('approve_transfer',))
        creator = _user('13944000032', '采购组长', role='leader', branch=branch, scope_branch=branch)

        tid = _web_purchase(_client(creator), item, branch)
        _client(m_a).post(f'/api/transfers/{tid}/approve', {'approved': False}, format='json')

        assert Notification.objects.filter(
            recipient=creator, title__contains='审批驳回',
        ).count() == 1
