from django.conf import settings
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
    # 回收库来源已退役（现场管理无回收库概念）：choices 只收新品库；
    # 常量保留给存量 recycle_bin 领用单的审批兼容（按其来源扣列）。
    ASSIGN_SOURCE_RECYCLE = 'recycle_bin'
    ASSIGN_SOURCE_CHOICES = [
        (ASSIGN_SOURCE_STOCK, '新品库'),
    ]

    RESTOCK = 'restock'
    DISPOSE = 'dispose'
    # 存量 recycle_bin 值的回收单为历史档案（当时入过回收库），不回写
    RECOVERY_DESTINATION_CHOICES = [
        (RESTOCK, '重新入库'),
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
    调入负责人 = models.CharField('调入负责人', max_length=100, blank=True, default='')
    供应商 = models.CharField('供应商', max_length=200, blank=True, default='')
    需求部门 = models.CharField('需求部门', max_length=100, blank=True, default='')
    经办人 = models.CharField('经办人', max_length=100, blank=True, default='')
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
        choices=RECOVERY_DESTINATION_CHOICES, default=RESTOCK,
    )
    领用来源 = models.CharField(
        '领用来源', max_length=20,
        choices=ASSIGN_SOURCE_CHOICES, default=ASSIGN_SOURCE_STOCK,
    )
    处置方式 = models.CharField('处置方式', max_length=20, blank=True, default='', choices=DISPOSAL_METHOD_CHOICES)
    处置金额 = models.DecimalField('处置金额', max_digits=14, decimal_places=2, null=True, blank=True)
    出库日期 = models.DateField('出库日期', null=True, blank=True)
    # 撤回等权限判定的唯一身份依据（purchase-withdraw-creator-fk）；
    # 「创建人」字符串是创建时姓名快照（记录性，展示/导出用），不参与权限判定
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_transfers',
        null=True,
        blank=True,
        verbose_name='创建账号(FK)',
    )

    class Meta:
        db_table = 'transfers_transfer'
        ordering = ['-调拨日期', '-created_at']
        verbose_name = '调拨记录'
        verbose_name_plural = '调拨记录'

    def __str__(self):
        return f'{self.单据编号 or self.pk} - {self.调拨日期}'

    # ---- 分公司语义化（transfer-branch-semantics）：类型到 from/to 的映射唯一收口于此 ----

    @classmethod
    def build(cls, action_type, fields, *, 所属分公司=None, 调出分公司=None, 调入分公司=None):
        """语义化建单：fields 为其余单头字段的 dict（与方向参数命名空间隔离）。

        单公司类型（采购/领用/归还/回收）只收 所属分公司，调拨收 调出+调入；
        from/to 落位由类型决定，调用方无从装反。非法参数组合（跨类型传参）直接
        拒绝——参数即业务校验。注意 fields 内的 调出/调入分公司 为文本回显字段，
        由本方法的 Branch 参数决定，不参与方向。
        """
        if action_type == cls.ACTION_PURCHASE:
            if 调出分公司 is not None or 调入分公司 is not None:
                raise ValueError('采购单只接受 所属分公司（调出/调入为调拨专属参数）')
            from_b, to_b = None, 所属分公司
        elif action_type == cls.ACTION_TRANSFER:
            if 所属分公司 is not None:
                raise ValueError('调拨单须分别传 调出分公司 与 调入分公司')
            from_b, to_b = 调出分公司, 调入分公司
        elif action_type == cls.ACTION_RETURN:
            if 调出分公司 is not None or 调入分公司 is not None:
                raise ValueError('归还单只接受 所属分公司（还入方）')
            from_b, to_b = None, 所属分公司  # 归还=还入方（to），与 ledger 历史口径一致
        else:
            if 调出分公司 is not None or 调入分公司 is not None:
                raise ValueError('该单据类型只接受 所属分公司（调出/调入为调拨专属参数）')
            from_b, to_b = 所属分公司, None
        return cls(action_type=action_type, from_branch=from_b, to_branch=to_b, **fields)

    @property
    def 业务分公司(self):
        """单据的货账归属方：采购/归还→入库方（to_branch）；领用/回收/调拨→出账方（from_branch）。"""
        if self.action_type in (self.ACTION_PURCHASE, self.ACTION_RETURN):
            return self.to_branch
        return self.from_branch

    def set_branches(self, *, 所属分公司=None, 调出分公司=None, 调入分公司=None):
        """语义化改派分公司（编辑路径）：与 build 同一套类型映射，禁直赋 from/to。"""
        if self.action_type == self.ACTION_PURCHASE:
            if 调出分公司 is not None or 调入分公司 is not None:
                raise ValueError('采购单只接受 所属分公司')
            self.to_branch = 所属分公司
            self.from_branch = None
        elif self.action_type == self.ACTION_TRANSFER:
            if 所属分公司 is not None:
                raise ValueError('调拨单须分别传 调出分公司 与 调入分公司')
            self.from_branch = 调出分公司
            self.to_branch = 调入分公司
        elif self.action_type == self.ACTION_RETURN:
            if 调出分公司 is not None or 调入分公司 is not None:
                raise ValueError('归还单只接受 所属分公司（还入方）')
            self.to_branch = 所属分公司
            self.from_branch = None
        else:
            if 调出分公司 is not None or 调入分公司 is not None:
                raise ValueError('该单据类型只接受 所属分公司')
            self.from_branch = 所属分公司
            self.to_branch = None
        return self

    @property
    def 业务分公司名(self):
        """文本版业务分公司（调入/调出文本按类型取）。"""
        if self.action_type in (self.ACTION_PURCHASE, self.ACTION_RETURN):
            return self.调入分公司
        return self.调出分公司


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
    供应商 = models.CharField('供应商（行级，空=继承单头）', max_length=200, blank=True, default='')
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


class ImportFingerprint(UUIDModel, TimestampedModel):
    """导入文件防重传指纹：同一上传者的同一文件 24h 内重传即拒（第 30 案）。"""

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='import_fingerprints', verbose_name='上传者',
    )
    sha1 = models.CharField('文件指纹', max_length=40)

    class Meta:
        db_table = 'transfers_importfingerprint'
        constraints = [
            models.UniqueConstraint(fields=['user', 'sha1'], name='uniq_import_fp_user_sha1'),
        ]
        verbose_name = '导入指纹'
        verbose_name_plural = '导入指纹'
