"""notification-routing-accuracy：业务分公司路由/空分公司不广播/已入库识别/created_by 定位。"""
import pytest
from rest_framework import status

from apps.notifications.models import Notification


def _user(phone, name, role='manager', branch=None, scope_branch=None,
          scope_region=None, scope_all=False, ops=()):
    from django.contrib.auth import get_user_model
    from apps.permissions.models import ManagementScope, OperationGrant
    u = get_user_model().objects.create_user(
        phone=phone, name=name, password='test123456',
        role=role, status='active', branch=branch,
    )
    if scope_all:
        ManagementScope.objects.create(user=u, is_all_data=True)
    elif scope_region is not None:
        ManagementScope.objects.create(user=u, region=scope_region)
    elif scope_branch is not None:
        ManagementScope.objects.create(user=u, branch=scope_branch)
    operation_codes = set(ops)
    prerequisites = {
        'edit_purchase': ('view_purchase', 'view_categories'),
        'edit_assignment': ('view_assignment', 'view_asset_ledger'),
        'edit_transfer': ('view_transfer', 'view_asset_ledger'),
        'edit_recovery': ('view_recovery', 'view_asset_ledger'),
        'approve_purchase': ('view_purchase',),
        'approve_assignment': ('view_assignment',),
        'approve_internal_transfer': ('view_transfer',),
        'approve_recovery': ('view_recovery',),
        'review_inventory': ('view_inventory',),
    }
    operation_codes.update(
        prerequisite
        for code in tuple(operation_codes)
        for prerequisite in prerequisites.get(code, ())
    )
    for code in operation_codes:
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
        m_a = _user('13944000001', 'A司经理', role='leader', scope_branch=branch, ops=('approve_purchase',))
        m_b = _user('13944000002', 'B司经理', scope_branch=second_branch, ops=('approve_purchase',))
        m_h = _user(
            '13944000003', '上级经理', role='director', scope_region=branch.team.region,
            ops=('approve_purchase',),
        )
        wrong_type = _user(
            '13944000005', '领用审批人', scope_branch=branch, ops=('approve_assignment',),
        )
        creator = _user(
            '13944000004', '采购组长', role='leader', branch=branch,
            scope_branch=branch, ops=('edit_purchase',),
        )

        _web_purchase(_client(creator), item, branch)

        def _pending(u):
            return Notification.objects.filter(recipient=u, notification_type='approval').count()

        assert _pending(m_a) == 1            # 调入方审批人收到
        assert _pending(m_b) == 0            # 无关分公司不广播
        assert _pending(m_h) == 1            # 审批资格按岗位与当前数据范围实时判定，不依赖逐单路由
        assert _pending(wrong_type) == 0     # 只通知拥有对应单据类型权限的人
        assert _pending(creator) == 0

    def test_purchase_approved_notifies_creator_and_cc(self, branch):
        from apps.notifications.models import ApprovalCC
        from apps.permissions.models import ManagementScope
        item = _ledger_item('NR-2')
        m_a = _user('13944000011', 'A司经理', role='leader', scope_branch=branch, ops=('approve_purchase',))
        cc_u = _user(
            '13944000012', '上级报告查看人', scope_region=branch.team.region,
            ops=('view_approval_reports',),
        )
        branch_reader = _user(
            '13944000014', '分公司报告查看人', scope_branch=branch,
            ops=('view_approval_reports',),
        )
        admin = _user('13944000015', '系统管理员', role='admin', branch=branch)
        creator = _user(
            '13944000013', '采购组长', role='leader', branch=branch,
            scope_branch=branch, ops=('edit_purchase',),
        )

        tid = _web_purchase(_client(creator), item, branch)
        resp = _client(m_a).post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == status.HTTP_200_OK

        # 采购落「已入库」：创建人经 created_by 收到结果通知，抄送照常
        assert Notification.objects.filter(
            recipient=creator, notification_type='task', title__contains='审批通过',
        ).count() == 1
        assert ApprovalCC.objects.filter(transfer_id=tid, recipient=cc_u).count() == 1
        assert ApprovalCC.objects.filter(transfer_id=tid, recipient=branch_reader).count() == 0
        assert ApprovalCC.objects.filter(transfer_id=tid, recipient=admin).count() == 1
        assert not ManagementScope.objects.filter(user=admin).exists()
        assert Notification.objects.filter(
            recipient=admin, related_object_type='transfer', related_object_id=tid,
            notification_type='cc',
        ).count() == 1

    def test_same_name_not_misnotified(self, branch):
        item = _ledger_item('NR-3')
        m_a = _user('13944000021', 'A司经理', role='leader', scope_branch=branch, ops=('approve_purchase',))
        creator = _user(
            '13944000022', '王小明', role='leader', branch=branch,
            scope_branch=branch, ops=('edit_purchase',),
        )
        namesake = _user('13944000023', '王小明', role='leader', branch=branch)  # 重名他人

        tid = _web_purchase(_client(creator), item, branch)
        _client(m_a).post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')

        assert Notification.objects.filter(recipient=creator, title__contains='审批通过').count() == 1
        assert Notification.objects.filter(recipient=namesake, title__contains='审批').count() == 0

    def test_purchase_rejected_notifies_creator(self, branch):
        from apps.notifications.models import ApprovalCC
        from apps.permissions.models import ManagementScope
        item = _ledger_item('NR-4')
        m_a = _user('13944000031', 'A司经理', role='leader', scope_branch=branch, ops=('approve_purchase',))
        upper = _user(
            '13944000033', '上级报告查看人', scope_region=branch.team.region,
            ops=('view_approval_reports',),
        )
        admin = _user('13944000034', '系统管理员', role='admin', branch=branch)
        creator = _user(
            '13944000032', '采购组长', role='leader', branch=branch,
            scope_branch=branch, ops=('edit_purchase',),
        )

        tid = _web_purchase(_client(creator), item, branch)
        _client(m_a).post(f'/api/transfers/{tid}/approve', {'approved': False}, format='json')

        assert Notification.objects.filter(
            recipient=creator, title__contains='审批驳回',
        ).count() == 1
        assert ApprovalCC.objects.filter(transfer_id=tid, recipient=upper).count() == 1
        assert ApprovalCC.objects.filter(transfer_id=tid, recipient=admin).count() == 1
        assert not ManagementScope.objects.filter(user=admin).exists()
        assert Notification.objects.filter(
            recipient=admin, related_object_type='transfer', related_object_id=tid,
            notification_type='cc',
        ).count() == 1

    def test_no_local_approver_falls_back_to_upper(self, branch):
        item = _ledger_item('NR-5')
        upper = _user(
            '13944000041', '上级采购审批人', role='director', scope_region=branch.team.region,
            ops=('approve_purchase',),
        )
        admin = _user('13944000047', '系统管理员', role='admin')
        creator = _user('13944000042', '采购创建人', branch=branch,
                        scope_branch=branch, ops=('edit_purchase',))

        tid = _web_purchase(_client(creator), item, branch)
        assert Notification.objects.filter(
            recipient=upper, related_object_id=tid, notification_type='approval',
        ).count() == 1
        assert Notification.objects.filter(
            recipient=admin, related_object_id=tid, notification_type='approval',
        ).count() == 1
        assert Notification.objects.filter(
            recipient=creator, related_object_id=tid, notification_type='approval',
        ).count() == 0

        response = _client(upper).post(
            f'/api/transfers/{tid}/approve', {'approved': True}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

    def test_recovery_uses_its_own_approval_permission(self, branch):
        from apps.transfers.authorization import get_transfer_approvers
        from apps.transfers.models import Transfer

        purchase_approver = _user(
            '13944000071', '采购审批人', branch=branch, scope_branch=branch,
            ops=('approve_purchase',),
        )
        recovery_approver = _user(
            '13944000072', '上级回收审批人', role='director', scope_region=branch.team.region,
            ops=('approve_recovery',),
        )

        assert get_transfer_approvers(branch, Transfer.ACTION_RECOVERY) == [recovery_approver]

        local_recovery_approver = _user(
            '13944000073', '本级回收审批人', role='leader', branch=branch, scope_branch=branch,
            ops=('approve_recovery',),
        )
        assert set(get_transfer_approvers(branch, Transfer.ACTION_RECOVERY)) == {
            local_recovery_approver, recovery_approver,
        }
        assert purchase_approver.id != recovery_approver.id

    def test_self_approval_is_allowed_and_notified(self, branch):
        item = _ledger_item('NR-8')
        creator = _user(
            '13944000043', '可自批采购人', role='leader', branch=branch,
            scope_branch=branch, ops=('edit_purchase', 'approve_purchase'),
        )
        tid = _web_purchase(_client(creator), item, branch)
        assert Notification.objects.filter(
            recipient=creator, related_object_id=tid, notification_type='approval',
        ).count() == 1

        response = _client(creator).post(
            f'/api/transfers/{tid}/approve', {'approved': True}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

    def test_approval_permission_is_specific_to_document_type(self, branch):
        item = _ledger_item('NR-9')
        creator = _user(
            '13944000044', '采购创建人', branch=branch, scope_branch=branch,
            ops=('edit_purchase',),
        )
        wrong_type_approver = _user(
            '13944000045', '领用审批人', branch=branch, scope_branch=branch,
            ops=('approve_assignment', 'view_purchase'),
        )
        tid = _web_purchase(_client(creator), item, branch)

        response = _client(wrong_type_approver).post(
            f'/api/transfers/{tid}/approve', {'approved': True}, format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Notification.objects.filter(
            recipient=wrong_type_approver, related_object_id=tid,
            notification_type='approval',
        ).count() == 0

    def test_purchase_creation_requires_its_type_permission(self, branch):
        item = _ledger_item('NR-10')
        creator = _user(
            '13944000046', '无采购创建权限员工', branch=branch,
            scope_branch=branch,
        )
        response = _client(creator).post('/api/transfers/purchase', {
            '调拨日期': '2026-09-30', '调入分公司': branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_grant_limits_owned_and_scope_view(self, branch, second_branch):
        from apps.permissions.models import OperationGrant

        item = _ledger_item('NR-6')
        first = _user(
            '13944000051', '创建人甲', branch=branch, scope_branch=branch,
            ops=('edit_purchase',),
        )
        peer = _user(
            '13944000052', '创建人乙', branch=branch, scope_branch=branch,
            ops=('edit_purchase',),
        )
        other_branch_user = _user(
            '13944000053', '异地创建人', branch=second_branch,
            scope_branch=second_branch, ops=('edit_purchase',),
        )
        own_id = _web_purchase(_client(first), item, branch)
        peer_id = _web_purchase(_client(peer), item, branch)
        other_id = _web_purchase(_client(other_branch_user), item, second_branch)

        first_client = _client(first)
        scoped_view = first_client.get('/api/transfers/')
        assert scoped_view.status_code == status.HTTP_200_OK
        visible_ids = {row['id'] for row in scoped_view.data['results']}
        assert visible_ids == {own_id, peer_id}
        assert other_id not in visible_ids

    def test_approver_sees_all_in_scope_pending_documents(self, branch):
        item = _ledger_item('NR-7')
        local = _user(
            '13944000061', '本级审批人', role='leader', branch=branch, scope_branch=branch,
            ops=('approve_purchase',),
        )
        upper = _user(
            '13944000062', '上级审批人', role='director', scope_region=branch.team.region,
            ops=('approve_purchase',),
        )
        creator = _user(
            '13944000063', '采购创建人', branch=branch, scope_branch=branch,
            ops=('edit_purchase',),
        )
        tid = _web_purchase(_client(creator), item, branch)

        local_response = _client(local).get('/api/transfers/')
        upper_response = _client(upper).get('/api/transfers/')
        assert {row['id'] for row in local_response.data['results']} == {tid}
        assert {row['id'] for row in upper_response.data['results']} == {tid}


@pytest.mark.django_db
class TestInventoryNotificationRouting:
    def _task(self, branch, created_by=None):
        from apps.inventories.models import InventoryTask

        return InventoryTask.objects.create(
            name='盘点通知路由测试', branch=branch, created_by=created_by,
        )

    def test_review_notification_uses_new_permission_and_prefers_local(self, branch):
        local = _user(
            '13944000101', '本级盘点审批人', role='leader', branch=branch,
            scope_branch=branch, ops=('review_inventory',),
        )
        upper = _user(
            '13944000102', '上级盘点审批人', role='director', scope_region=branch.team.region,
            ops=('review_inventory',),
        )
        legacy = _user(
            '13944000103', '旧盘点审批权限', branch=branch,
            scope_branch=branch, ops=('approve_inventory',),
        )
        task = self._task(branch)

        task.status = 'pending_review'
        task.save(update_fields=['status'])

        assert Notification.objects.filter(
            recipient=local, related_object_id=task.id, notification_type='approval',
        ).count() == 1
        assert Notification.objects.filter(
            recipient=upper, related_object_id=task.id, notification_type='approval',
        ).exists()
        assert not Notification.objects.filter(
            recipient=legacy, related_object_id=task.id, notification_type='approval',
        ).exists()

        task.name = '盘点通知路由测试（未改状态）'
        task.save(update_fields=['name'])
        assert Notification.objects.filter(
            recipient=local, related_object_id=task.id, notification_type='approval',
        ).count() == 1

    def test_review_notification_falls_back_to_upper_when_no_local_reviewer(
        self, branch, admin_user,
    ):
        upper = _user(
            '13944000111', '上级盘点审批人', role='director', scope_region=branch.team.region,
            ops=('review_inventory',),
        )
        legacy = _user(
            '13944000112', '旧权限持有人', branch=branch,
            scope_branch=branch, ops=('approve_inventory',),
        )
        task = self._task(branch)

        task.status = 'pending_review'
        task.save(update_fields=['status'])

        for recipient in (upper, admin_user):
            assert Notification.objects.filter(
                recipient=recipient, related_object_id=task.id,
                notification_type='approval',
            ).count() == 1
        assert not Notification.objects.filter(
            recipient=legacy, related_object_id=task.id, notification_type='approval',
        ).exists()

    @pytest.mark.parametrize('result_status', ['completed', 'rejected'])
    def test_approval_result_report_goes_only_to_upper_report_readers(
        self, branch, second_branch, result_status,
    ):
        from apps.notifications.models import ApprovalCC
        from apps.permissions.models import ManagementScope

        upper = _user(
            '13944000121', '上级报告查看人', scope_region=branch.team.region,
            ops=('view_approval_reports',),
        )
        local = _user(
            '13944000122', '本级报告查看人', branch=branch,
            scope_branch=branch, ops=('view_approval_reports',),
        )
        legacy = _user(
            '13944000123', '旧抄送权限持有人', scope_region=branch.team.region,
            ops=('view_all_notifications',),
        )
        unrelated = _user(
            '13944000124', '无关分公司报告查看人',
            scope_region=second_branch.team.region, ops=('view_approval_reports',),
        )
        admin = _user('13944000125', '系统管理员', role='admin', branch=branch)
        task = self._task(branch)
        task.status = 'pending_review'
        task.save(update_fields=['status'])
        task.status = result_status
        task.save(update_fields=['status'])

        assert ApprovalCC.objects.filter(
            inventory_task=task, recipient=upper,
        ).count() == 1
        assert ApprovalCC.objects.filter(
            inventory_task=task, recipient=admin,
        ).count() == 1
        assert ApprovalCC.objects.filter(inventory_task=task).count() == 2
        assert not ManagementScope.objects.filter(user=admin).exists()
        for recipient in (upper, admin):
            assert Notification.objects.filter(
                recipient=recipient, related_object_type='inventory_task',
                related_object_id=task.id, notification_type='cc',
            ).count() == 1
        for recipient in (local, legacy, unrelated):
            assert not ApprovalCC.objects.filter(
                inventory_task=task, recipient=recipient,
            ).exists()

        task.name = '后续编辑不重复抄送'
        task.save(update_fields=['name'])
        assert ApprovalCC.objects.filter(inventory_task=task).count() == 2

    def test_system_admin_receives_reports_for_all_branches_without_scope(
        self, branch, second_branch,
    ):
        from apps.notifications.models import ApprovalCC
        from apps.permissions.models import ManagementScope

        admin = _user('13944000126', '全局系统管理员', role='admin', branch=branch)
        assert not ManagementScope.objects.filter(user=admin).exists()

        for report_branch in (branch, second_branch):
            task = self._task(report_branch)
            task.status = 'pending_review'
            task.save(update_fields=['status'])
            task.status = 'completed'
            task.save(update_fields=['status'])

            assert ApprovalCC.objects.filter(
                inventory_task=task, recipient=admin,
            ).count() == 1
            assert Notification.objects.filter(
                recipient=admin, related_object_type='inventory_task',
                related_object_id=task.id, notification_type='cc',
            ).count() == 1
