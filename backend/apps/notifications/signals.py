"""
消息通知触发 Signals
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.transfers.models import Transfer
from apps.transfers.authorization import (
    get_transfer_approvers,
    get_transfer_approvers_for_document,
    get_transfer_inbound_rejectors,
    get_upper_approval_report_recipients,
)
from apps.inventories.models import InventoryTask
from apps.inventories.authorization import get_inventory_review_approvers
from apps.users.models import User
from .models import Notification, ApprovalCC


def _adjustment_summary(task):
    """盘点完成后汇总差异生成的调整单数（盘盈/盘亏分计），附进通知 extra_data。"""
    summary = {'total': 0, 'surplus': 0, 'missing': 0}
    for delta in task.adjustments.values_list('变动量', flat=True):
        summary['total'] += 1
        if delta > 0:
            summary['surplus'] += 1
        else:
            summary['missing'] += 1
    return summary


def _users_with_operation_access(branch, code, include_admin=True, exclude_admin=False):
    """返回持指定业务操作授权且数据范围覆盖该分公司的活跃用户。

    与运行时鉴权同口径：持 OperationGrant 授权（admin 内置全部，可选纳入/排除）。
    branch 可为 Branch 实例、id 或名称字符串；无法解析时 MUST NOT 广播
    （notification-routing-accuracy）：仅 admin 与「全部数据」授权者接收——
    分公司未知时只有全量范围者确定覆盖。
    """
    from django.db.models import Q
    from apps.organizations.models import Branch
    from apps.permissions.scope import resolve_user_scope

    if isinstance(branch, str):
        branch = Branch.objects.filter(name=branch).first()
    elif isinstance(branch, int):
        branch = Branch.objects.filter(id=branch).first()

    q = Q(operation_grants__code=code)
    if include_admin:
        q |= Q(role='admin')
    candidates = User.objects.filter(q, status='active').distinct()
    if exclude_admin:
        candidates = candidates.exclude(role='admin')
    result = []
    for u in candidates:
        scope = resolve_user_scope(u)
        if scope.all or (branch is not None and branch.id in scope.branches):
            result.append(u)
    return result


def _notify_inventory_approval_report(task):
    recipients = get_upper_approval_report_recipients(task.branch)
    result = task.get_status_display()
    snapshot = {
        'task_name': task.name,
        'branch': task.branch.name if task.branch else '',
        'status': task.status,
        'status_display': result,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'rejected_at': task.rejected_at.isoformat() if task.rejected_at else None,
        'rejected_by': task.rejected_by.name if task.rejected_by else '',
        'reject_reason': task.reject_reason or '',
    }
    for recipient in recipients:
        ApprovalCC.objects.create(
            inventory_task=task,
            cc_type='auto',
            cc_reason=f'盘点审批结果（{result}）向上级报告',
            recipient=recipient,
            approval_snapshot=snapshot,
        )
        Notification.objects.create(
            recipient=recipient,
            notification_type='cc',
            title=f'盘点审批报告：{task.name}',
            content=f'{snapshot["branch"]}的盘点任务“{task.name}”审批结果：{result}。',
            priority='low',
            related_object_type='inventory_task',
            related_object_id=task.id,
        )


def _is_recipient_self(instance, user):
    """自通知排除：优先 created_by 外键比较，存量无 FK 单据回退姓名。"""
    if instance.created_by_id:
        return instance.created_by_id == user.id
    return bool(instance.创建人) and user.name == instance.创建人


def _locate_creator(instance):
    """创建人定位：created_by 外键优先（精确到人），FK 为空的存量单据回退姓名匹配。"""
    if instance.created_by_id:
        return instance.created_by
    if instance.创建人:
        return User.objects.filter(name=instance.创建人).first()
    return None


def _routing_branch(instance):
    """路由分公司：业务分公司 FK 优先（purchase/return=调入方，其余=调出方），
    文本快照兜底（ORM 直造/存量单据可能只有文本无 FK）。解析失败返回 None。"""
    branch = instance.业务分公司
    if branch is not None:
        return branch
    from apps.organizations.models import Branch
    if instance.action_type in (Transfer.ACTION_PURCHASE, Transfer.ACTION_RETURN):
        text = instance.调入分公司
    else:
        text = instance.调出分公司
    return Branch.objects.filter(name=text).first() if text else None


def get_approvers_for_branch(branch, action_type=None):
    """获取某分公司、某单据类型当前应处理的审批人。"""
    if action_type is None:
        return []
    return get_transfer_approvers(branch, action_type)


def _doc_summary(instance):
    """多明细单据摘要：首行品目名 +（行数>1 时）等 N 项；返回 None 表示明细行未就绪。"""
    lines = list(instance.lines.select_related('item').order_by('行号'))
    if not lines:
        return None
    first = lines[0]
    name = first.item.asset_name + (f' 等 {len(lines)} 项' if len(lines) > 1 else '')
    return {
        'asset_name': name,
        'asset_code': first.item.asset_code,
        'qty': sum(line.数量 for line in lines),
    }


def _notify_transfer_approval_report(instance, summary, result_label):
    branch = _routing_branch(instance)
    recipients = get_upper_approval_report_recipients(branch)
    action_display = dict(Transfer.ACTION_CHOICES).get(
        instance.action_type, instance.action_type,
    )
    snapshot = {
        'asset_name': summary['asset_name'],
        'asset_code': summary['asset_code'],
        'doc_number': instance.单据编号,
        'from_branch': instance.调出分公司,
        'to_branch': instance.调入分公司,
        'approver': instance.审批人,
        'approved_at': instance.审批时间.isoformat() if instance.审批时间 else None,
        'action_type': instance.action_type,
        'action_display': action_display,
        'qty': summary['qty'],
        'result': result_label,
        'reason': instance.备注 or '',
    }
    for recipient in recipients:
        ApprovalCC.objects.create(
            transfer=instance,
            cc_type='auto',
            cc_reason=f'{result_label}后向上级报告',
            recipient=recipient,
            approval_snapshot=snapshot,
        )
        Notification.objects.create(
            recipient=recipient,
            notification_type='cc',
            title=f'审批报告：{summary["asset_name"]} {result_label}',
            content=(
                f'{instance.审批人} 已{result_label}{action_display}申请，'
                f'{instance.调出分公司} → {instance.调入分公司}'
            ),
            priority='low',
            related_object_type='transfer',
            related_object_id=instance.id,
        )


def notify_transfer_created(instance):
    """单据进入待审批时通知审批人。

    由视图在明细行齐备后显式调用（单头 post_save 触发时行尚未建，信号侧静默跳过）。
    """
    if instance.审批状态 != '待审批':
        return
    summary = _doc_summary(instance)
    if summary is None:
        return
    # 本级存在该单据类型审批人时只路由本级；否则沿用上级数据范围兜底。
    approvers = get_transfer_approvers_for_document(instance)

    # 动作类型映射
    action_display = dict(Transfer.ACTION_CHOICES).get(
        instance.action_type, instance.action_type,
    )

    for approver in approvers:
        Notification.objects.create(
            recipient=approver,
            notification_type='approval',
            title=f'待审批：{summary["asset_name"]}',
            content=f'{instance.创建人 or "用户"} 提交了{action_display}申请，请及时审批。',
            priority='high',
            related_object_type='transfer',
            related_object_id=instance.id,
            extra_data={
                'action_type': instance.action_type,
                'asset_name': summary['asset_name'],
                'asset_code': summary['asset_code'],
                'qty': summary['qty'],
                'doc_number': instance.单据编号,
                'from_branch': instance.调出分公司,
                'to_branch': instance.调入分公司,
            },
        )

    # 调入方驳回通道：调拨单通知持 edit_transfer 权限且满足查看前置的调入方人员。
    if instance.action_type == Transfer.ACTION_TRANSFER and instance.调入分公司:
        inbound_managers = get_transfer_inbound_rejectors(instance.to_branch or instance.调入分公司)
        for manager in inbound_managers:
            if _is_recipient_self(instance, manager):
                continue
            Notification.objects.create(
                recipient=manager,
                notification_type='approval',
                title=f'调入待确认：{summary["asset_name"]}',
                content=f'{instance.调出分公司} 向贵公司调拨 {summary["qty"]}{summary.get("unit", "")}，如拒收请在审批通过前驳回。',
                priority='high',
                related_object_type='transfer',
                related_object_id=instance.id,
                extra_data={
                    'action_type': instance.action_type,
                    'asset_name': summary['asset_name'],
                    'asset_code': summary['asset_code'],
                    'qty': summary['qty'],
                    'doc_number': instance.单据编号,
                    'from_branch': instance.调出分公司,
                    'to_branch': instance.调入分公司,
                },
            )


@receiver(post_save, sender=Transfer)
def notify_on_transfer_created(sender, instance, created, **kwargs):
    """兜底路径（admin/shell 等直接建单）：创建即待审批且明细行已就绪时通知。"""
    if created:
        notify_transfer_created(instance)


@receiver(pre_save, sender=Transfer)
def handle_transfer_approval_change(sender, instance, **kwargs):
    """处理调拨单审批状态变更"""
    if not instance.pk:
        return

    try:
        old_instance = Transfer.objects.get(pk=instance.pk)
    except Transfer.DoesNotExist:
        return

    # 检测状态从"待审批"变为生效（已通过；采购为已入库——notification-routing-accuracy）
    if old_instance.审批状态 == '待审批' and instance.审批状态 in ('已通过', '已入库'):
        summary = _doc_summary(instance) or {
            'asset_name': instance.单据编号 or '单据', 'asset_code': '', 'qty': 0,
        }
        # 1. 通知创建人（created_by 外键定位，重名不错发）
        creator = _locate_creator(instance)
        if creator:
                action_display = dict(Transfer.ACTION_CHOICES).get(
                    instance.action_type, instance.action_type,
                )
                Notification.objects.create(
                    recipient=creator,
                    notification_type='task',
                    title=f'审批通过：{summary["asset_name"]}',
                    content=f'您的{action_display}申请已由 {instance.审批人} 审批通过。',
                    priority='medium',
                    related_object_type='transfer',
                    related_object_id=instance.id,
                )

        _notify_transfer_approval_report(instance, summary, '通过')

    # 检测状态从"待审批"变为"已驳回"
    elif old_instance.审批状态 == '待审批' and instance.审批状态 == '已驳回':
        summary = _doc_summary(instance) or {
            'asset_name': instance.单据编号 or '单据', 'asset_code': '', 'qty': 0,
        }
        # 通知创建人（created_by 外键定位）
        creator = _locate_creator(instance)
        if creator:
                action_display = dict(Transfer.ACTION_CHOICES).get(
                    instance.action_type, instance.action_type,
                )
                Notification.objects.create(
                    recipient=creator,
                    notification_type='task',
                    title=f'审批驳回：{summary["asset_name"]}',
                    content=f'您的{action_display}申请被 {instance.审批人} 驳回。{instance.备注 or ""}',
                    priority='high',
                    related_object_type='transfer',
                    related_object_id=instance.id,
                )
        _notify_transfer_approval_report(instance, summary, '驳回')


@receiver(post_save, sender=InventoryTask)
def notify_on_inventory_status_change(sender, instance, created, **kwargs):
    """盘点任务状态变更通知"""
    if created:
        # 新建任务通知相关人员
        return

    if getattr(instance, '_previous_status', None) == instance.status:
        return

    # 状态变更通知
    status_notifications = {
        'pending_review': ('task', '盘点任务待审核', 'medium'),
        'completed': ('task', '盘点任务已完成', 'medium'),
        'rejected': ('task', '盘点任务已驳回', 'high'),
    }

    if instance.status in status_notifications:
        notify_type, title_prefix, priority = status_notifications[instance.status]

        # 通知创建人（完成后 extra_data 附差异生成的调整单数，盘盈/盘亏分计）
        if instance.created_by:
            extra = (
                _adjustment_summary(instance)
                if instance.status == 'completed' else {}
            )
            Notification.objects.create(
                recipient=instance.created_by,
                notification_type=notify_type,
                title=f'{title_prefix}：{instance.name}',
                content=f'盘点任务状态已变更为：{instance.get_status_display()}',
                priority=priority,
                related_object_type='inventory_task',
                related_object_id=instance.id,
                extra_data=extra,
            )

    # 提交审核时通知审批人
    if instance.status == 'pending_review':
        approvers = get_inventory_review_approvers(instance)

        for approver in approvers:
            Notification.objects.create(
                recipient=approver,
                notification_type='approval',
                title=f'待审核盘点任务：{instance.name}',
                content=f'{instance.created_by.name if instance.created_by else "用户"} 提交了盘点任务，请审核。',
                priority='high',
                related_object_type='inventory_task',
                related_object_id=instance.id,
            )

    # 上级只在审批结果形成后收到只读报告；分公司内用户不参与抄送。
    if instance.status in ('completed', 'rejected'):
        _notify_inventory_approval_report(instance)


@receiver(pre_save, sender=InventoryTask)
def capture_previous_inventory_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = InventoryTask.objects.filter(
        pk=instance.pk,
    ).values_list('status', flat=True).first()
