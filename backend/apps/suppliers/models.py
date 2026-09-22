from django.db import models
from core.models import UUIDModel, TimestampedModel


class Supplier(UUIDModel, TimestampedModel):
    """供应商字典 —— 全集团扁平（supplier-dictionary），采购建单行级引用的身份源。

    各分公司供应商高度重合且量少，不设分公司维度；建单明细行的「供应商」仍存名称
    文本（记录性快照，同「创建人」模式），字典只做选择来源与归一口径。
    """

    name = models.CharField('供应商名称', max_length=200, unique=True)
    联系人 = models.CharField('联系人', max_length=100, blank=True, default='')
    电话 = models.CharField('电话', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'suppliers_supplier'
        ordering = ['name']
        verbose_name = '供应商'
        verbose_name_plural = '供应商字典'

    def __str__(self):
        return self.name
