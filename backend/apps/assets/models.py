from django.db import models
from core.models import UUIDModel, TimestampedModel


class AssetStock(UUIDModel, TimestampedModel):
    """资产汇总台账 —— 库存唯一事实源，一行 = 分公司 × 品目。

    铁律：在库数量为唯一事实存储值；在用/回收库为唯一写入口（services/ledger.py）
    维护的物化派生列，事实源是单据流水；总量恒等于三列之和（不落库）。
    """

    branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='ledger_rows',
        verbose_name='分公司',
    )
    item = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='ledger_rows',
        verbose_name='品目',
    )
    在库数量 = models.IntegerField('在库数量', default=0)
    在用数量 = models.IntegerField('在用数量', default=0)
    回收库数量 = models.IntegerField('回收库数量', default=0)
    警戒线 = models.IntegerField('警戒线（空则用品目默认）', null=True, blank=True)

    class Meta:
        db_table = 'assets_assetstock'
        ordering = ['branch__name', 'item__asset_code']
        verbose_name = '资产汇总台账'
        verbose_name_plural = '资产汇总台账'
        constraints = [
            models.UniqueConstraint(fields=['branch', 'item'], name='uniq_ledger_branch_item'),
        ]

    def __str__(self):
        return f'{self.branch.name} {self.item.asset_code} (在库{self.在库数量})'

    @property
    def 生效警戒线(self):
        """行级警戒线优先，空则回落品目字典默认。"""
        return self.警戒线 if self.警戒线 is not None else self.item.warning_line

    @property
    def 是否充足(self):
        line = self.生效警戒线
        return (line is None) or ((self.在库数量 or 0) >= line)

    @property
    def 总量(self):
        return (self.在库数量 or 0) + (self.在用数量 or 0) + (self.回收库数量 or 0)


class LedgerAdjustment(UUIDModel, TimestampedModel):
    """台账调整单 —— 数量变动的非流转出口（含期初入账），铁律 2 的合规载体。

    创建即生效（无审批流，P3 按需补充）；台账变动由 services/ledger.py 执行。
    """

    TARGET_STOCK = '在库数量'
    TARGET_IN_USE = '在用数量'
    TARGET_RECYCLE = '回收库数量'
    TARGET_CHOICES = [
        (TARGET_STOCK, '在库'),
        (TARGET_IN_USE, '在用'),
        (TARGET_RECYCLE, '回收库'),
    ]

    branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='ledger_adjustments',
        verbose_name='分公司',
    )
    item = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='ledger_adjustments',
        verbose_name='品目',
    )
    目标列 = models.CharField('目标列', max_length=20, choices=TARGET_CHOICES)
    变动量 = models.IntegerField('变动量（可正可负）')
    事由 = models.CharField('事由', max_length=200)
    经办人 = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_adjustments',
        verbose_name='经办人',
    )
    is_initial = models.BooleanField('期初单', default=False)

    class Meta:
        db_table = 'assets_ledger_adjustment'
        ordering = ['-created_at']
        verbose_name = '台账调整单'
        verbose_name_plural = '台账调整单'

    def __str__(self):
        return f'{self.branch.name} {self.item.asset_code} {self.目标列}{self.变动量:+d}'


class Asset(UUIDModel, TimestampedModel):
    """资产（品目级别）— 一条记录代表一类资产的库存汇总。"""
    STATUS_CHOICES = [
        ('在库', '在库'),
        ('使用中', '使用中'),
        ('维修中', '维修中'),
        ('报废', '报废'),
    ]

    序号 = models.IntegerField('序号')
    分公司 = models.CharField('分公司', max_length=100)
    分公司编号 = models.CharField('分公司编号', max_length=50, db_index=True)
    branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='assets',
        null=True,
        blank=True,
        verbose_name='所属分公司',
    )
    资产编号 = models.CharField('资产编号', max_length=100, db_index=True)
    资产类目 = models.CharField('资产类目', max_length=100, db_index=True)
    物品分类 = models.CharField('物品分类', max_length=100)
    资产名称 = models.CharField('资产名称', max_length=200)
    规格 = models.CharField('规格', max_length=200, blank=True, default='')
    供应商 = models.CharField('供应商', max_length=200, blank=True, default='')
    图片 = models.ImageField('图片', upload_to='assets/', blank=True, null=True)
    入库日期 = models.DateField('入库日期', null=True, blank=True, db_index=True)
    是否租用 = models.BooleanField('是否租用', default=False)
    数量 = models.IntegerField('数量', default=1)
    单价 = models.DecimalField('单价', max_digits=12, decimal_places=2, null=True, blank=True)
    购入金额 = models.DecimalField('购入金额', max_digits=14, decimal_places=2, null=True, blank=True)
    出库日期 = models.DateField('出库日期', null=True, blank=True)
    所属部门 = models.CharField('所属部门', max_length=100, blank=True, default='')
    使用人 = models.CharField('使用人', max_length=100, blank=True, default='')
    当前状态 = models.CharField('当前状态', max_length=20, choices=STATUS_CHOICES, default='在库', db_index=True)
    警戒线 = models.IntegerField('警戒线', null=True, blank=True)
    是否充足 = models.BooleanField('是否充足', default=True)
    电脑序列号 = models.CharField('电脑序列号', max_length=200, blank=True, default='')
    备注 = models.TextField('备注', blank=True, default='')

    class Meta:
        db_table = 'assets_asset'
        ordering = ['-序号']
        verbose_name = '资产'
        verbose_name_plural = '资产'

    def __str__(self):
        return f'{self.资产名称} ({self.资产编号})'


class FixedAsset(UUIDModel, TimestampedModel):
    """固定资产实例 — 一物一档（仅实例管理品目）。

    四态档案：在库 → 在用 → 回收库 → 退役（终态，档案永久保留）。
    品目信息经 item 联字典、供应商/单价经出生明细行派生，本表不存品目文本（铁律 1）；
    状态/使用人/分公司的全部变动经 services/instances.py（由台账唯一写入口同事务调用）。
    """
    STATUS_IN_STOCK = '在库'
    STATUS_IN_USE = '在用'
    STATUS_RECYCLE = '回收库'
    STATUS_RETIRED = '退役'
    INSTANCE_STATUS_CHOICES = [
        (STATUS_IN_STOCK, '在库'),
        (STATUS_IN_USE, '在用'),
        (STATUS_RECYCLE, '回收库'),
        (STATUS_RETIRED, '退役'),
    ]

    item = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='instances',
        verbose_name='品目',
    )
    内部编号 = models.CharField('内部编号', max_length=100, unique=True)
    序列号 = models.CharField('序列号（空=待补录）', max_length=200, blank=True, default='')
    当前状态 = models.CharField(
        '当前状态', max_length=20,
        choices=INSTANCE_STATUS_CHOICES, default=STATUS_IN_STOCK, db_index=True,
    )
    使用人 = models.CharField('使用人（记录性）', max_length=100, blank=True, default='')
    department = models.ForeignKey(
        'organizations.Department',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='instances', verbose_name='归属部门',
    )
    branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='fixed_assets',
        null=True, blank=True,
        verbose_name='所属分公司',
    )
    birth_line = models.ForeignKey(
        'transfers.TransferLine',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='born_instances', verbose_name='出生明细行',
    )
    入库日期 = models.DateField('入库日期', null=True, blank=True)
    备注 = models.TextField('备注', blank=True, default='')

    class Meta:
        db_table = 'assets_fixedasset'
        ordering = ['内部编号']
        verbose_name = '固定资产实例'
        verbose_name_plural = '固定资产实例'

    def __str__(self):
        return f'{self.内部编号} ({self.item.asset_name})'


class InstanceSequence(UUIDModel, TimestampedModel):
    """实例内部编号计数行：品目一行，锁行自增杜绝并发重号（同 DocumentSequence 模式）。"""

    item = models.OneToOneField(
        'categories.Category',
        on_delete=models.CASCADE,
        related_name='instance_sequence',
        verbose_name='品目',
    )
    last_no = models.IntegerField('已发号数', default=0)

    class Meta:
        db_table = 'assets_instancesequence'
        verbose_name = '实例编号序列'
        verbose_name_plural = '实例编号序列'

    def __str__(self):
        return f'{self.item.asset_code} #{self.last_no}'
