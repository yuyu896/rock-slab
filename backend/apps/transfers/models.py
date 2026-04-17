from django.db import models
from core.models import UUIDModel, TimestampedModel


class Transfer(UUIDModel, TimestampedModel):
    """调拨/流转记录 - uses Chinese Python field names directly."""
    APPROVAL_CHOICES = [
        ('待审批', '待审批'),
        ('已通过', '已通过'),
        ('已驳回', '已驳回'),
    ]

    ACTION_ASSIGN = 'assign'
    ACTION_RETURN = 'return'
    ACTION_TRANSFER = 'transfer'
    ACTION_REPAIR = 'repair'
    ACTION_SCRAP = 'scrap'
    ACTION_PURCHASE = 'purchase'
    ACTION_CHOICES = [
        (ACTION_PURCHASE, '采购入库'),
        (ACTION_ASSIGN, '领用'),
        (ACTION_RETURN, '归还'),
        (ACTION_TRANSFER, '调拨'),
        (ACTION_REPAIR, '维修'),
        (ACTION_SCRAP, '报废'),
    ]

    调拨日期 = models.DateField('调拨日期')
    调出分公司 = models.CharField('调出分公司', max_length=100, blank=True, default='')
    调出部门 = models.CharField('调出部门', max_length=100, blank=True, default='')
    from_branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='transfers_from',
        null=True,
        blank=True,
        verbose_name='调出分公司(FK)',
    )
    调入分公司 = models.CharField('调入分公司', max_length=100, blank=True, default='')
    to_branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='transfers_to',
        null=True,
        blank=True,
        verbose_name='调入分公司(FK)',
    )
    调入部门 = models.CharField('调入部门', max_length=100, blank=True, default='')
    资产编号 = models.CharField('资产编号', max_length=100)
    资产名称 = models.CharField('资产名称', max_length=200)
    规格型号 = models.CharField('规格型号', max_length=200, blank=True, default='')
    调拨数量 = models.IntegerField('调拨数量', default=1)
    调拨原因 = models.TextField('调拨原因', blank=True, default='')
    调出负责人 = models.CharField('调出负责人', max_length=100, blank=True, default='')
    调入负责人 = models.CharField('调入负责人', max_length=100, blank=True, default='')
    备注 = models.TextField('备注', blank=True, default='')
    审批状态 = models.CharField('审批状态', max_length=20, choices=APPROVAL_CHOICES, default='待审批')
    审批人 = models.CharField('审批人', max_length=100, blank=True, default='')
    审批时间 = models.DateTimeField('审批时间', null=True, blank=True)
    创建人 = models.CharField('创建人', max_length=100, blank=True, default='')
    action_type = models.CharField('操作类型', max_length=20, choices=ACTION_CHOICES, default=ACTION_TRANSFER)

    class Meta:
        db_table = 'transfers_transfer'
        ordering = ['-调拨日期', '-created_at']
        verbose_name = '调拨记录'
        verbose_name_plural = '调拨记录'

    def __str__(self):
        return f'{self.资产名称} - {self.调拨日期}'
