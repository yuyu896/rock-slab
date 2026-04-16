from django.db import models
from core.models import UUIDModel, TimestampedModel


class InventoryTask(UUIDModel, TimestampedModel):
    """盘点任务"""
    STATUS_CHOICES = [
        ('pending', '待盘点'),
        ('in_progress', '盘点中'),
        ('pending_review', '待审核'),
        ('completed', '已完成'),
        ('rejected', '已驳回'),
        ('cancelled', '已作废'),
    ]
    MISSED_RULE_CHOICES = [
        ('keep', '保持不变'),
        ('zero', '清零处理'),
    ]
    REPEAT_RULE_CHOICES = [
        ('last', '以最后一次为准'),
        ('accumulate', '累计数量'),
    ]

    name = models.CharField('任务名称', max_length=200)
    branch = models.ForeignKey(
        'organizations.Branch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inventory_tasks',
        verbose_name='盘点分公司',
    )
    category = models.ForeignKey(
        'categories.Category', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inventory_tasks',
        verbose_name='资产类目',
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=STATUS_CHOICES, default='pending',
    )
    missed_rule = models.CharField(
        '漏盘规则', max_length=20,
        choices=MISSED_RULE_CHOICES, default='keep',
    )
    repeat_rule = models.CharField(
        '重复盘点规则', max_length=20,
        choices=REPEAT_RULE_CHOICES, default='last',
    )
    created_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_inventory_tasks',
        verbose_name='创建人',
    )
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    rejected_at = models.DateTimeField('驳回时间', null=True, blank=True)
    rejected_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='rejected_inventory_tasks',
        verbose_name='驳回人',
    )
    reject_reason = models.TextField('驳回原因', blank=True, default='')

    # State machine: valid transitions
    TRANSITIONS = {
        'pending': ['in_progress', 'cancelled'],
        'in_progress': ['pending_review', 'cancelled'],
        'pending_review': ['completed', 'rejected'],
        'rejected': ['in_progress', 'cancelled'],
        'completed': [],
        'cancelled': [],
    }

    class Meta:
        db_table = 'inventories_task'
        ordering = ['-created_at']
        verbose_name = '盘点任务'
        verbose_name_plural = '盘点任务'
        indexes = [
            models.Index(fields=['branch', 'status'], name='inventories_task_branch_status'),
        ]

    def __str__(self):
        return self.name

    def can_transition(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, [])


class InventoryItem(UUIDModel, TimestampedModel):
    """盘点项"""
    RESULT_CHOICES = [
        ('matched', '正常'),
        ('surplus', '盘盈'),
        ('missing', '盘亏'),
        ('unchecked', '未盘点'),
    ]

    task = models.ForeignKey(
        InventoryTask, on_delete=models.CASCADE,
        related_name='items', verbose_name='盘点任务',
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='inventory_items', verbose_name='资产',
    )
    expected_qty = models.IntegerField('应盘数量', default=0)
    actual_qty = models.IntegerField('实盘数量', null=True, blank=True)
    result = models.CharField(
        '盘点结果', max_length=20,
        choices=RESULT_CHOICES, default='unchecked',
    )
    check_count = models.IntegerField('盘点次数', default=0)
    checked_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='checked_items',
        verbose_name='盘点人',
    )
    checked_at = models.DateTimeField('盘点时间', null=True, blank=True)
    remarks = models.TextField('备注', blank=True, default='')

    class Meta:
        db_table = 'inventories_item'
        ordering = ['created_at']
        verbose_name = '盘点项'
        verbose_name_plural = '盘点项'

    def __str__(self):
        return f'{self.task.name} - {self.asset.资产名称}'


class InventoryCheck(UUIDModel, TimestampedModel):
    """盘点记录 - supports multi-person collaborative inventory."""
    task = models.ForeignKey(
        InventoryTask, on_delete=models.CASCADE,
        related_name='checks', verbose_name='盘点任务',
    )
    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE,
        related_name='check_records', verbose_name='盘点项',
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='inventory_checks', verbose_name='资产',
    )
    qty = models.IntegerField('盘点数量')
    checked_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inventory_checks',
        verbose_name='盘点人',
    )
    checked_at = models.DateTimeField('盘点时间', auto_now_add=True)
    device = models.CharField('设备信息', max_length=200, blank=True, default='')

    class Meta:
        db_table = 'inventories_check'
        ordering = ['-checked_at']
        verbose_name = '盘点记录'
        verbose_name_plural = '盘点记录'

    def __str__(self):
        return f'{self.task.name} - {self.asset.资产名称} - {self.qty}'
