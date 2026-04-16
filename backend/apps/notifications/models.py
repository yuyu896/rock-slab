from django.db import models
from core.models import UUIDModel, TimestampedModel


class Notification(UUIDModel, TimestampedModel):
    """消息通知"""
    TYPE_CHOICES = [
        ('approval', '审批提醒'),
        ('task', '任务通知'),
        ('cc', '抄送通知'),
        ('system', '系统通知'),
    ]

    PRIORITY_CHOICES = [
        ('high', '高'),
        ('medium', '中'),
        ('low', '低'),
    ]

    recipient = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='接收人',
    )
    notification_type = models.CharField(
        '通知类型', max_length=20,
        choices=TYPE_CHOICES,
    )
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    priority = models.CharField(
        '优先级', max_length=10,
        choices=PRIORITY_CHOICES, default='medium',
    )
    is_read = models.BooleanField('是否已读', default=False)
    read_at = models.DateTimeField('阅读时间', null=True, blank=True)

    # 关联对象
    related_object_type = models.CharField(
        '关联对象类型', max_length=50, blank=True,
    )
    related_object_id = models.UUIDField(
        '关联对象ID', null=True, blank=True,
    )

    # 扩展数据
    extra_data = models.JSONField(
        '额外数据', default=dict, blank=True,
    )

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        verbose_name = '消息通知'
        verbose_name_plural = '消息通知'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f'{self.recipient.name} - {self.title}'


class ApprovalCC(UUIDModel, TimestampedModel):
    """审批抄送记录"""
    CC_TYPE_CHOICES = [
        ('auto', '自动抄送'),
        ('manual', '手动抄送'),
    ]

    # 关联的审批单
    transfer = models.ForeignKey(
        'transfers.Transfer', on_delete=models.CASCADE,
        related_name='cc_records',
        verbose_name='调拨单',
        null=True, blank=True,
    )
    inventory_task = models.ForeignKey(
        'inventories.InventoryTask', on_delete=models.CASCADE,
        related_name='cc_records',
        verbose_name='盘点任务',
        null=True, blank=True,
    )

    # 抄送信息
    cc_type = models.CharField(
        '抄送类型', max_length=20,
        choices=CC_TYPE_CHOICES,
        default='auto',
    )
    cc_reason = models.CharField(
        '抄送原因', max_length=200, blank=True,
    )

    # 接收人
    recipient = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='received_ccs',
        verbose_name='接收人',
    )

    # 状态
    is_read = models.BooleanField('是否已读', default=False)
    read_at = models.DateTimeField('阅读时间', null=True, blank=True)

    # 审批信息快照
    approval_snapshot = models.JSONField(
        '审批快照', default=dict,
    )

    class Meta:
        db_table = 'notifications_approval_cc'
        ordering = ['-created_at']
        verbose_name = '审批抄送'
        verbose_name_plural = '审批抄送'

    def __str__(self):
        return f'CC to {self.recipient.name}'
