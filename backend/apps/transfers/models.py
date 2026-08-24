from django.db import models
from core.models import UUIDModel, TimestampedModel


class Transfer(UUIDModel, TimestampedModel):
    """流转单单头：谁/何时/为何/审批；品目×数量在明细行 TransferLine。"""
    APPROVAL_CHOICES = [
        ('草稿', '草稿'),
        ('待审批', '待审批'),
        ('已通过', '已通过'),
        ('已驳回', '已驳回'),
        ('已入库', '已入库'),
    ]

    ACTION_ASSIGN = 'assign'
    ACTION_RETURN = 'return'
    ACTION_TRANSFER = 'transfer'
    ACTION_PURCHASE = 'purchase'
    ACTION_RECOVERY = 'recovery'
    ACTION_CHOICES = [
        (ACTION_PURCHASE, '采购入库'),
        (ACTION_ASSIGN, '领用'),
        (ACTION_RETURN, '归还'),
        (ACTION_TRANSFER, '调拨'),
        (ACTION_RECOVERY, '回收'),
    ]

    RECOVERY_CATEGORY_CHOICES = [
        ('闲置回收', '闲置回收'),
        ('报废回收', '报废回收'),
        ('捐赠回收', '捐赠回收'),
        ('其他', '其他'),
    ]

    ASSIGN_SOURCE_STOCK = 'stock'
    ASSIGN_SOURCE_RECYCLE = 'recycle_bin'
    ASSIGN_SOURCE_CHOICES = [
        (ASSIGN_SOURCE_STOCK, '新品库'),
        (ASSIGN_SOURCE_RECYCLE, '回收库'),
    ]

    RECYCLE_BIN = 'recycle_bin'
    DISPOSE = 'dispose'
    RECOVERY_DESTINATION_CHOICES = [
        (RECYCLE_BIN, '入回收库'),
        (DISPOSE, '直接处置'),
    ]
    DISPOSAL_METHOD_CHOICES = [
        ('出售', '出售'),
        ('报废', '报废'),
        ('捐赠', '捐赠'),
    ]

    单据编号 = models.CharField('单据编号', max_length=32, unique=True, null=True, blank=True, db_index=True)
    调拨日期 = models.DateField('调拨日期', db_index=True)
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
    调拨原因 = models.TextField('调拨原因', blank=True, default='')
    调出负责人 = models.CharField('调出负责人', max_length=100, blank=True, default='')
    调入负责人 = models.CharField('调入负责人', max_length=100, blank=True, default='')
    供应商 = models.CharField('供应商', max_length=200, blank=True, default='')
    需求部门 = models.CharField('需求部门', max_length=100, blank=True, default='')
    采购经办人 = models.CharField('采购经办人', max_length=100, blank=True, default='')
    用途 = models.CharField('用途', max_length=200, blank=True, default='')
    备注 = models.TextField('备注', blank=True, default='')
    审批状态 = models.CharField('审批状态', max_length=20, choices=APPROVAL_CHOICES, default='待审批', db_index=True)
    审批人 = models.CharField('审批人', max_length=100, blank=True, default='')
    审批时间 = models.DateTimeField('审批时间', null=True, blank=True)
    创建人 = models.CharField('创建人', max_length=100, blank=True, default='')
    action_type = models.CharField(
        '操作类型', max_length=20, choices=ACTION_CHOICES,
        default=ACTION_TRANSFER, db_index=True,
    )
    回收分类 = models.CharField('回收分类', max_length=50, blank=True, default='', choices=RECOVERY_CATEGORY_CHOICES)
    回收去向 = models.CharField(
        '回收去向', max_length=20,
        choices=RECOVERY_DESTINATION_CHOICES, default=RECYCLE_BIN,
    )
    领用来源 = models.CharField(
        '领用来源', max_length=20,
        choices=ASSIGN_SOURCE_CHOICES, default=ASSIGN_SOURCE_STOCK,
    )
    处置方式 = models.CharField('处置方式', max_length=20, blank=True, default='', choices=DISPOSAL_METHOD_CHOICES)
    处置金额 = models.DecimalField('处置金额', max_digits=14, decimal_places=2, null=True, blank=True)
    出库日期 = models.DateField('出库日期', null=True, blank=True)

    class Meta:
        db_table = 'transfers_transfer'
        ordering = ['-调拨日期', '-created_at']
        verbose_name = '调拨记录'
        verbose_name_plural = '调拨记录'

    def __str__(self):
        return f'{self.单据编号 or self.pk} - {self.调拨日期}'


class TransferLine(UUIDModel, TimestampedModel):
    """流转单明细行：品目 × 数量 × 类型专属记录性字段（采购单价/金额、领用使用人/部门、回收存放位置）× 实例关联。"""

    transfer = models.ForeignKey(
        Transfer, on_delete=models.CASCADE, related_name='lines', verbose_name='单头',
    )
    item = models.ForeignKey(
        'categories.Category', on_delete=models.PROTECT, related_name='transfer_lines', verbose_name='品目',
    )
    行号 = models.IntegerField('行号')
    数量 = models.PositiveIntegerField('数量')
    本批规格 = models.CharField('本批规格（记录性）', max_length=200, blank=True, default='')
    单价 = models.DecimalField('单价', max_digits=12, decimal_places=2, null=True, blank=True)
    金额 = models.DecimalField('金额', max_digits=14, decimal_places=2, null=True, blank=True)
    使用人 = models.CharField('使用人（记录性）', max_length=100, blank=True, default='')
    department = models.ForeignKey(
        'organizations.Department', on_delete=models.PROTECT, null=True, blank=True,
        related_name='transfer_lines', verbose_name='领用部门',
    )
    存放位置 = models.CharField('存放位置', max_length=200, blank=True, default='')
    instances = models.ManyToManyField(
        'assets.FixedAsset',
        through='TransferLineInstance',
        related_name='transfer_lines',
        blank=True,
        verbose_name='关联实例',
    )

    class Meta:
        db_table = 'transfers_transferline'
        ordering = ['行号']
        verbose_name = '流转单明细行'
        verbose_name_plural = '流转单明细行'
        constraints = [
            models.UniqueConstraint(fields=['transfer', '行号'], name='uniq_transfer_line_no'),
        ]

    def __str__(self):
        return f'{self.transfer_id} #{self.行号} {self.item_id} × {self.数量}'


class TransferLineInstance(UUIDModel, TimestampedModel):
    """行-实例关联：一个实例一生出现在多行（出生/领用/归还/调拨/回收），角色由单据类型隐含。"""

    line = models.ForeignKey(
        TransferLine, on_delete=models.CASCADE, related_name='instance_links', verbose_name='明细行',
    )
    instance = models.ForeignKey(
        'assets.FixedAsset', on_delete=models.PROTECT, related_name='line_links', verbose_name='实例',
    )

    class Meta:
        db_table = 'transfers_transferlineinstance'
        verbose_name = '明细行实例关联'
        verbose_name_plural = '明细行实例关联'
        constraints = [
            models.UniqueConstraint(fields=['line', 'instance'], name='uniq_line_instance'),
        ]

    def __str__(self):
        return f'{self.line_id} × {self.instance_id}'


class DocumentSequence(UUIDModel, TimestampedModel):
    """单据编号计数行：(类型, 日期) 一行，锁行自增杜绝并发重号。"""

    action_type = models.CharField('单据类型', max_length=20, db_index=True)
    date = models.DateField('日期')
    last_no = models.IntegerField('已发号数', default=0)

    class Meta:
        db_table = 'transfers_documentsequence'
        verbose_name = '单据编号序列'
        verbose_name_plural = '单据编号序列'
        constraints = [
            models.UniqueConstraint(fields=['action_type', 'date'], name='uniq_doc_seq_type_date'),
        ]

    def __str__(self):
        return f'{self.action_type} {self.date} #{self.last_no}'
