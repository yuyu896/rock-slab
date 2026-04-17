from django.db import models
from core.models import UUIDModel, TimestampedModel


class Asset(UUIDModel, TimestampedModel):
    """资产 - uses Chinese Python field names directly."""
    STATUS_CHOICES = [
        ('在库', '在库'),
        ('使用中', '使用中'),
        ('维修中', '维修中'),
        ('报废', '报废'),
    ]

    序号 = models.IntegerField('序号')
    分公司 = models.CharField('分公司', max_length=100)
    分公司编号 = models.CharField('分公司编号', max_length=50)
    branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='assets',
        null=True,
        blank=True,
        verbose_name='所属分公司',
    )
    资产编号 = models.CharField('资产编号', max_length=100, unique=True)
    资产类目 = models.CharField('资产类目', max_length=100)
    物品分类 = models.CharField('物品分类', max_length=100)
    资产名称 = models.CharField('资产名称', max_length=200)
    规格 = models.CharField('规格', max_length=200, blank=True, default='')
    供应商 = models.CharField('供应商', max_length=200, blank=True, default='')
    图片 = models.ImageField('图片', upload_to='assets/', blank=True, null=True)
    入库日期 = models.DateField('入库日期', null=True, blank=True)
    是否租用 = models.BooleanField('是否租用', default=False)
    数量 = models.IntegerField('数量', default=1)
    单价 = models.DecimalField('单价', max_digits=12, decimal_places=2, null=True, blank=True)
    购入金额 = models.DecimalField('购入金额', max_digits=14, decimal_places=2, null=True, blank=True)
    出库日期 = models.DateField('出库日期', null=True, blank=True)
    所属部门 = models.CharField('所属部门', max_length=100, blank=True, default='')
    使用人 = models.CharField('使用人', max_length=100, blank=True, default='')
    当前状态 = models.CharField('当前状态', max_length=20, choices=STATUS_CHOICES, default='在库')
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
