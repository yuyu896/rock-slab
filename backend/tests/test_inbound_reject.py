"""transfer-inbound-reject 回归：调入方在待审批阶段对调拨单的驳回通道与通知。"""
import datetime

import pytest

from conftest import _client_for
from apps.transfers.models import Transfer, TransferLine
from apps.notifications.models import Notification
from apps.permissions.models import OperationGrant, ManagementScope


def _grant(user, code):
    OperationGrant.objects.get_or_create(user=user, code=code)
    return user


@pytest.fixture
def item_instance(branch):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='固定', item_category='办公',
        asset_name='ThinkPad T14', asset_code='NB-IR1', unit='台',
        management_type='instance',
    )


def _doc(from_branch, to_branch, code, *, creator=None, status='待审批', item=None):
    t = Transfer.objects.create(
        单据编号=code, 调拨日期=datetime.date(2026, 9, 29),
        调出分公司=from_branch.name, from_branch=from_branch,
        调入分公司=to_branch.name, to_branch=to_branch,
        action_type='transfer', 审批状态=status,
        created_by=creator, 创建人=(creator.name if creator else ''),
    )
    if item is not None:
        TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=2)
    return t


@pytest.mark.django_db
class TestInboundReject:
    def test_inbound_side_can_reject(self, supervisor_b, staff_user, branch, second_branch):
        doc = _doc(branch, second_branch, 'IR-1', creator=staff_user)
        client = _client_for(supervisor_b)
        resp = client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': '库存不符'}, format='json')
        assert resp.status_code == 200
        doc.refresh_from_db()
        assert doc.审批状态 == '已驳回'
        assert doc.调入方驳回原因 == '库存不符'
        assert doc.审批人 == '区域B主管'
        assert '【调入方驳回】库存不符' in doc.备注

    def test_reason_required(self, supervisor_b, branch, second_branch):
        doc = _doc(branch, second_branch, 'IR-2')
        client = _client_for(supervisor_b)
        resp = client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': '  '}, format='json')
        assert resp.status_code == 400 and '驳回原因' in str(resp.data)

    def test_stage_limited(self, supervisor_b, branch, second_branch):
        client = _client_for(supervisor_b)
        for i, status in enumerate(['草稿', '已通过', '已驳回']):
            doc = _doc(branch, second_branch, f'IR-S{i}', status=status)
            resp = client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': 'x'}, format='json')
            assert resp.status_code == 400, status

    def test_outbound_side_forbidden(self, staff_user, branch, second_branch):
        _grant(staff_user, 'manage_assets')
        doc = _doc(branch, second_branch, 'IR-3')
        client = _client_for(staff_user)
        resp = client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': 'x'}, format='json')
        assert resp.status_code == 400 and '授权范围' in str(resp.data)

    def test_non_transfer_type_rejected(self, supervisor_b, branch, second_branch):
        doc = Transfer.objects.create(
            单据编号='IR-4', 调拨日期=datetime.date(2026, 9, 29),
            调入分公司=second_branch.name, to_branch=second_branch,
            action_type='purchase', 审批状态='待审批',
        )
        client = _client_for(supervisor_b)
        resp = client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': 'x'}, format='json')
        assert resp.status_code == 400 and '调拨' in str(resp.data)

    def test_codeless_user_forbidden(self, second_branch, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13700000098', name='无码调入方', password='test123456',
            role='manager', status='active', branch=second_branch,
        )
        ManagementScope.objects.create(user=user, branch=second_branch)
        doc = _doc(branch, second_branch, 'IR-5')
        client = _client_for(user)
        resp = client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': 'x'}, format='json')
        assert resp.status_code == 403

    def test_second_attempt_after_processing(self, supervisor_b, staff_user, branch, second_branch):
        doc = _doc(branch, second_branch, 'IR-6', creator=staff_user)
        client = _client_for(supervisor_b)
        assert client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': 'a'}, format='json').status_code == 200
        resp = client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': 'b'}, format='json')
        assert resp.status_code == 400

    def test_creator_can_resubmit_after_reject(self, supervisor_b, staff_user, branch, second_branch):
        doc = _doc(branch, second_branch, 'IR-7', creator=staff_user)
        client = _client_for(supervisor_b)
        assert client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': 'a'}, format='json').status_code == 200
        resp = _client_for(staff_user).post(f'/api/transfers/{doc.pk}/resubmit')
        assert resp.status_code == 200
        doc.refresh_from_db()
        assert doc.审批状态 == '待审批'

    def test_serializer_flags(self, supervisor_b, staff_user, branch, second_branch):
        doc = _doc(branch, second_branch, 'IR-8')
        resp = _client_for(supervisor_b).get(f'/api/transfers/{doc.pk}')
        assert resp.data['canInboundReject'] is True
        resp = _client_for(staff_user).get(f'/api/transfers/{doc.pk}')
        assert resp.data['canInboundReject'] is False


@pytest.mark.django_db
class TestInboundNotifications:
    def test_inbound_manager_notified_on_pending(self, supervisor_b, staff_user, branch, second_branch, item_instance):
        from apps.notifications.signals import notify_transfer_created
        doc = _doc(branch, second_branch, 'IR-N1', creator=staff_user, item=item_instance)
        notify_transfer_created(doc)
        assert Notification.objects.filter(
            recipient=supervisor_b, related_object_id=doc.id, title__startswith='调入待确认',
        ).exists()

    def test_creator_notified_after_inbound_reject(self, supervisor_b, staff_user, branch, second_branch, item_instance):
        doc = _doc(branch, second_branch, 'IR-N2', creator=staff_user, item=item_instance)
        client = _client_for(supervisor_b)
        assert client.post(f'/api/transfers/{doc.pk}/inbound-reject', {'reason': '数量有误'}, format='json').status_code == 200
        assert Notification.objects.filter(
            recipient=staff_user, related_object_id=doc.id, title__startswith='审批驳回',
        ).exists()
