"""
消息通知触发 Signals
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.transfers.models import Transfer
from apps.inventories.models import InventoryTask
from apps.users.models import User
from .models import Notification, ApprovalCC


def get_approvers_for_branch(branch_name):
    """获取有权限审批某分公司的用户"""
    # 审批权限：supervisor 及以上
    return User.objects.filter(
        role__in=['admin', 'director', 'manager', 'supervisor'],
        status='active',
    )


@receiver(post_save, sender=Transfer)
def notify_on_transfer_created(sender, instance, created, **kwargs):
    """调拨单创建时通知审批人"""
    if created and instance.审批状态 == '待审批':
        # 获取有审批权限的用户
        approvers = get_approvers_for_branch(instance.调出分公司)

        # 动作类型映射
        action_display = dict(Transfer.ACTION_CHOICES).get(
            instance.action_type, instance.action_type,
        )

        for approver in approvers:
            # 避免自己通知自己
            if instance.创建人 and approver.name == instance.创建人:
                continue

            Notification.objects.create(
                recipient=approver,
                notification_type='approval',
                title=f'待审批：{instance.资产名称}',
                content=f'{instance.创建人 or "用户"} 提交了{action_display}申请，请及时审批。',
                priority='high',
                related_object_type='transfer',
                related_object_id=instance.id,
                extra_data={
                    'action_type': instance.action_type,
                    'asset_name': instance.资产名称,
                    'asset_code': instance.资产编号,
                    'from_branch': instance.调出分公司,
                    'to_branch': instance.调入分公司,
                },
            )


@receiver(pre_save, sender=Transfer)
def handle_transfer_approval_change(sender, instance, **kwargs):
    """处理调拨单审批状态变更"""
    if not instance.pk:
        return

    try:
        old_instance = Transfer.objects.get(pk=instance.pk)
    except Transfer.DoesNotExist:
        return

    # 检测状态从"待审批"变为"已通过"
    if old_instance.审批状态 == '待审批' and instance.审批状态 == '已通过':
        # 1. 通知创建人
        if instance.创建人:
            creator = User.objects.filter(name=instance.创建人).first()
            if creator:
                action_display = dict(Transfer.ACTION_CHOICES).get(
                    instance.action_type, instance.action_type,
                )
                Notification.objects.create(
                    recipient=creator,
                    notification_type='task',
                    title=f'审批通过：{instance.资产名称}',
                    content=f'您的{action_display}申请已由 {instance.审批人} 审批通过。',
                    priority='medium',
                    related_object_type='transfer',
                    related_object_id=instance.id,
                )

        # 2. 抄送给所有行政经理
        managers = User.objects.filter(
            role__in=['manager', 'director'],
            status='active',
        )

        action_display = dict(Transfer.ACTION_CHOICES).get(
            instance.action_type, instance.action_type,
        )

        for manager in managers:
            # 创建抄送记录
            ApprovalCC.objects.create(
                transfer=instance,
                cc_type='auto',
                cc_reason='审批通过自动抄送',
                recipient=manager,
                approval_snapshot={
                    'asset_name': instance.资产名称,
                    'asset_code': instance.资产编号,
                    'from_branch': instance.调出分公司,
                    'to_branch': instance.调入分公司,
                    'approver': instance.审批人,
                    'approved_at': instance.审批时间.isoformat() if instance.审批时间 else None,
                    'action_type': instance.action_type,
                    'action_display': action_display,
                    'qty': instance.调拨数量,
                },
            )

            # 同时创建通知
            Notification.objects.create(
                recipient=manager,
                notification_type='cc',
                title=f'抄送：{instance.资产名称} 审批已通过',
                content=f'{instance.审批人} 已通过{action_display}申请，{instance.调出分公司} → {instance.调入分公司}',
                priority='low',
                related_object_type='transfer',
                related_object_id=instance.id,
            )

    # 检测状态从"待审批"变为"已驳回"
    elif old_instance.审批状态 == '待审批' and instance.审批状态 == '已驳回':
        # 通知创建人
        if instance.创建人:
            creator = User.objects.filter(name=instance.创建人).first()
            if creator:
                action_display = dict(Transfer.ACTION_CHOICES).get(
                    instance.action_type, instance.action_type,
                )
                Notification.objects.create(
                    recipient=creator,
                    notification_type='task',
                    title=f'审批驳回：{instance.资产名称}',
                    content=f'您的{action_display}申请被 {instance.审批人} 驳回。{instance.备注 or ""}',
                    priority='high',
                    related_object_type='transfer',
                    related_object_id=instance.id,
                )


@receiver(post_save, sender=InventoryTask)
def notify_on_inventory_status_change(sender, instance, created, **kwargs):
    """盘点任务状态变更通知"""
    if created:
        # 新建任务通知相关人员
        return

    # 状态变更通知
    status_notifications = {
        'pending_review': ('task', '盘点任务待审核', 'medium'),
        'completed': ('task', '盘点任务已完成', 'medium'),
        'rejected': ('task', '盘点任务已驳回', 'high'),
    }

    if instance.status in status_notifications:
        notify_type, title_prefix, priority = status_notifications[instance.status]

        # 通知创建人
        if instance.created_by:
            Notification.objects.create(
                recipient=instance.created_by,
                notification_type=notify_type,
                title=f'{title_prefix}：{instance.name}',
                content=f'盘点任务状态已变更为：{instance.get_status_display()}',
                priority=priority,
                related_object_type='inventory_task',
                related_object_id=instance.id,
            )

    # 提交审核时通知审批人
    if instance.status == 'pending_review':
        approvers = User.objects.filter(
            role__in=['admin', 'director', 'manager', 'supervisor'],
            status='active',
        )

        for approver in approvers:
            if instance.created_by and approver.id == instance.created_by.id:
                continue

            Notification.objects.create(
                recipient=approver,
                notification_type='approval',
                title=f'待审核盘点任务：{instance.name}',
                content=f'{instance.created_by.name if instance.created_by else "用户"} 提交了盘点任务，请审核。',
                priority='high',
                related_object_type='inventory_task',
                related_object_id=instance.id,
            )

    # 审批通过后抄送给行政经理
    if instance.status == 'completed':
        managers = User.objects.filter(
            role__in=['manager', 'director'],
            status='active',
        )

        for manager in managers:
            ApprovalCC.objects.create(
                inventory_task=instance,
                cc_type='auto',
                cc_reason='盘点完成自动抄送',
                recipient=manager,
                approval_snapshot={
                    'task_name': instance.name,
                    'status': instance.status,
                    'completed_at': instance.completed_at.isoformat() if instance.completed_at else None,
                },
            )

            Notification.objects.create(
                recipient=manager,
                notification_type='cc',
                title=f'抄送：盘点任务 {instance.name} 已完成',
                content='盘点任务已完成审批。',
                priority='low',
                related_object_type='inventory_task',
                related_object_id=instance.id,
            )
