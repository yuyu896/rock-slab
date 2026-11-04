from datetime import date

import pytest
from rest_framework import status

from conftest import _client_for


def _employee(phone, name, role, branch, active=True):
    from apps.users.models import User

    return User.objects.create_user(
        phone=phone,
        name=name,
        password='test123456',
        role=role,
        branch=branch,
        status='active' if active else 'inactive',
        is_active=active,
    )


def _grant_user_management(user):
    from apps.permissions.models import OperationGrant

    OperationGrant.objects.bulk_create([
        OperationGrant(user=user, code='view_users'),
        OperationGrant(user=user, code='edit_users'),
    ])


@pytest.mark.django_db
def test_hard_delete_requires_both_employee_permissions_and_in_scope_target(branch, second_branch):
    from apps.permissions.models import ManagementScope

    operator = _employee('13919991001', '员工管理员', 'manager', branch)
    target = _employee('13919991002', '目标员工', 'leader', second_branch)
    client = _client_for(operator)

    assert client.delete(f'/api/users/{target.pk}').status_code == status.HTTP_403_FORBIDDEN
    _grant_user_management(operator)

    response = client.delete(f'/api/users/{target.pk}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert target.__class__.objects.filter(pk=target.pk).exists()

    ManagementScope.objects.create(user=operator, branch=branch)
    response = client.delete(f'/api/users/{target.pk}')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    ManagementScope.objects.create(user=operator, branch=second_branch)
    response = client.delete(f'/api/users/{target.pk}')

    assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
    assert not target.__class__.objects.filter(pk=target.pk).exists()


@pytest.mark.django_db
def test_delete_user_rejects_last_active_system_admin(admin_user):
    response = _client_for(admin_user).delete(f'/api/users/{admin_user.pk}')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    admin_user.refresh_from_db()
    assert admin_user.is_active


@pytest.mark.django_db
def test_delete_user_requires_successor_for_each_responsible_node(admin_user, branch):
    from apps.organizations.models import Branch
    from apps.users.models import User

    target = _employee('13919991003', '原分公司负责人', 'manager', branch)
    successor = _employee('13919991004', '新分公司负责人', 'manager', branch)
    Branch.objects.filter(pk=branch.pk).update(manager=target)
    client = _client_for(admin_user)

    preview = client.get(f'/api/users/{target.pk}/delete-preview')
    assert preview.status_code == status.HTTP_200_OK
    assert preview.data['responsibilities'][0]['key'] == f'branch:{branch.pk}'
    assert preview.data['responsibilities'][0]['candidates'] == [
        {'id': str(successor.pk), 'name': successor.name},
    ]

    missing_successor = client.delete(
        f'/api/users/{target.pk}', {'successors': []}, format='json',
    )
    assert missing_successor.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.filter(pk=target.pk).exists()
    branch.refresh_from_db()
    assert branch.manager_id == target.pk

    response = client.delete(
        f'/api/users/{target.pk}',
        {'successors': [{
            'node_type': 'branch', 'node_id': str(branch.pk), 'user_id': str(successor.pk),
        }]},
        format='json',
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
    branch.refresh_from_db()
    assert branch.manager_id == successor.pk
    assert not User.objects.filter(pk=target.pk).exists()


@pytest.mark.django_db
def test_delete_cleans_only_unsubmitted_active_transfer_drafts_and_personal_messages(
    admin_user, branch,
):
    from apps.notifications.models import ApprovalCC, Notification
    from apps.transfers.models import Transfer
    from apps.users.models import User

    target = _employee('13919991005', '草稿创建人', 'manager', branch)
    drafts = [
        Transfer.objects.create(
            调拨日期=date(2026, 1, 1), action_type=action, 审批状态='草稿',
            创建人=target.name, created_by=target,
        )
        for action in (
            Transfer.ACTION_PURCHASE,
            Transfer.ACTION_ASSIGN,
            Transfer.ACTION_TRANSFER,
            Transfer.ACTION_RECOVERY,
        )
    ]
    pending = Transfer.objects.create(
        调拨日期=date(2026, 1, 2), action_type=Transfer.ACTION_PURCHASE,
        审批状态='待审批', 创建人=target.name, created_by=target,
    )
    rejected = Transfer.objects.create(
        调拨日期=date(2026, 1, 3), action_type=Transfer.ACTION_ASSIGN,
        审批状态='已驳回', 创建人=target.name, created_by=target,
    )
    pending_status = pending.审批状态
    rejected_status = rejected.审批状态
    notice = Notification.objects.create(
        recipient=target, notification_type='system', title='个人通知', content='提醒',
    )
    cc = ApprovalCC.objects.create(recipient=target, approval_snapshot={'creator': target.name})

    response = _client_for(admin_user).delete(f'/api/users/{target.pk}')

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(pk=target.pk).exists()
    assert not Transfer.objects.filter(pk__in=[row.pk for row in drafts]).exists()
    assert Transfer.objects.filter(pk=pending.pk, created_by__isnull=True).exists()
    assert Transfer.objects.filter(pk=rejected.pk, created_by__isnull=True).exists()
    assert Transfer.objects.get(pk=pending.pk).审批状态 == pending_status
    assert Transfer.objects.get(pk=rejected.pk).审批状态 == rejected_status
    assert not Notification.objects.filter(pk=notice.pk).exists()
    assert not ApprovalCC.objects.filter(pk=cc.pk).exists()

    admin_client = _client_for(admin_user)
    edit_response = admin_client.patch(
        f'/api/transfers/{rejected.pk}', {'调拨日期': '2026-01-04'}, format='json',
    )
    assert edit_response.status_code == status.HTTP_200_OK, edit_response.data
    resubmit_response = admin_client.post(f'/api/transfers/{rejected.pk}/resubmit')
    assert resubmit_response.status_code == status.HTTP_200_OK, resubmit_response.data
    assert Transfer.objects.get(pk=rejected.pk).审批状态 == '待审批'


@pytest.mark.django_db
def test_delete_preserves_inventory_reconciliation_ledger_and_audit_names(
    admin_user, branch,
):
    from apps.assets.models import AssetStock, LedgerAdjustment
    from apps.audit.models import AuditLog
    from apps.categories.models import Category
    from apps.inventories.models import InventoryCheck, InventoryItem, InventoryTask
    from apps.reconciliation.models import (
        ReconciliationIssue,
        ReconciliationIssueHistory,
        ReconciliationTask,
        ReconciliationUploadVersion,
    )
    from apps.suppliers.models import Supplier
    from apps.users.models import User

    target = _employee('13919991006', '历史记录员工', 'manager', branch)
    category = Category.objects.get(asset_code='PUR-001')
    stock = AssetStock.objects.create(branch=branch, item=category, 在库数量=5)
    task = InventoryTask.objects.create(
        name='员工删除历史盘点', branch=branch, created_by=target,
        created_by_name=target.name, rejected_by=target, rejected_by_name=target.name,
    )
    item = InventoryItem.objects.create(
        task=task, stock=stock, checked_by=target, checked_by_name=target.name,
    )
    check = InventoryCheck.objects.create(
        task=task, item=item, stock=stock, qty=4, checked_by=target,
        checked_by_name=target.name,
    )
    adjustment = LedgerAdjustment.objects.create(
        branch=branch, item=category, 目标列='在库数量', 变动量=1,
        事由='保留历史', 经办人=target, 经办人姓名=target.name,
    )
    supplier = Supplier.objects.create(name='硬删除历史供应商')
    recon = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 1, 1), created_by=target,
        created_by_name=target.name,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=recon, version_number=1, file='history.xlsx', uploaded_by=target,
        uploaded_by_name=target.name,
    )
    issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='hard-delete-history', issue_type='system_only',
        first_period=date(2026, 1, 1), last_period=date(2026, 1, 1),
        handled_by=target, handled_by_name=target.name,
        closed_by=target, closed_by_name=target.name,
    )
    history = ReconciliationIssueHistory.objects.create(
        issue=issue, user=target, user_name=target.name, new_status='closed',
    )
    actor_log = AuditLog.objects.create(
        user=target, user_name=target.name, user_phone=target.phone,
        action='update', resource_type='HistoricalRecord', description='历史操作',
    )
    other_actor_log = AuditLog.objects.create(
        user=admin_user,
        user_name=admin_user.name,
        user_phone=admin_user.phone,
        action='update',
        resource_type='HistoricalRecord',
        after_data={
            'deleted_employee': {'phone': target.phone},
            'other_employee': {'phone': '13919991999'},
            'actor': {'user_phone': admin_user.phone},
        },
    )

    response = _client_for(admin_user).delete(f'/api/users/{target.pk}')

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(pk=target.pk).exists()
    task.refresh_from_db()
    item.refresh_from_db()
    check.refresh_from_db()
    adjustment.refresh_from_db()
    recon.refresh_from_db()
    version.refresh_from_db()
    issue.refresh_from_db()
    history.refresh_from_db()
    actor_log.refresh_from_db()
    other_actor_log.refresh_from_db()
    assert task.created_by_id is None and task.created_by_name == target.name
    assert task.rejected_by_id is None and task.rejected_by_name == target.name
    assert item.checked_by_id is None and item.checked_by_name == target.name
    assert check.checked_by_id is None and check.checked_by_name == target.name
    assert adjustment.经办人_id is None and adjustment.经办人姓名 == target.name
    assert recon.created_by_id is None and recon.created_by_name == target.name
    assert version.uploaded_by_id is None and version.uploaded_by_name == target.name
    assert issue.handled_by_id is None and issue.handled_by_name == target.name
    assert issue.closed_by_id is None and issue.closed_by_name == target.name
    assert history.user_id is None and history.user_name == target.name
    assert actor_log.user_id is None and actor_log.user_name == target.name
    assert actor_log.user_phone == ''
    assert other_actor_log.user_id == admin_user.pk
    assert other_actor_log.user_phone == admin_user.phone
    assert other_actor_log.after_data == {
        'deleted_employee': {'phone': ''},
        'other_employee': {'phone': '13919991999'},
        'actor': {'user_phone': admin_user.phone},
    }

    deletion_log = AuditLog.objects.get(
        action='delete', resource_type='User', resource_id=str(target.pk),
    )
    assert deletion_log.before_data['phone'] == ''
    assert target.phone not in str(deletion_log.before_data)


@pytest.mark.django_db
def test_delete_reviews_ambiguous_legacy_drafts_and_preserves_unselected_drafts(admin_user, branch):
    from apps.transfers.models import Transfer
    from apps.users.models import User

    target = _employee('13919991007', '旧草稿匹配员工', 'manager', branch)
    drafts = [
        Transfer.objects.create(
            调拨日期=date(2026, 2, day),
            action_type=Transfer.ACTION_PURCHASE,
            审批状态='草稿',
            创建人=snapshot,
        )
        for day, snapshot in ((1, target.name), (2, target.phone))
    ]
    client = _client_for(admin_user)

    preview = client.get(f'/api/users/{target.pk}/delete-preview')
    assert preview.status_code == status.HTTP_200_OK
    assert {row['id'] for row in preview.data['legacy_draft_candidates']} == {
        str(draft.pk) for draft in drafts
    }

    unreviewed = client.delete(f'/api/users/{target.pk}', {'legacy_draft_ids': []}, format='json')
    assert unreviewed.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.filter(pk=target.pk).exists()
    assert Transfer.objects.filter(pk__in=[draft.pk for draft in drafts]).count() == 2

    response = client.delete(
        f'/api/users/{target.pk}',
        {
            'legacy_draft_reviewed_ids': [str(draft.pk) for draft in drafts],
            'legacy_draft_ids': [str(drafts[0].pk)],
        },
        format='json',
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
    assert not User.objects.filter(pk=target.pk).exists()
    assert not Transfer.objects.filter(pk=drafts[0].pk).exists()
    assert Transfer.objects.filter(pk=drafts[1].pk).exists()
