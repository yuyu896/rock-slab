from django.db import models
from core.models import UUIDModel, TimestampedModel


class Category(UUIDModel, TimestampedModel):
    """资产类目"""
    asset_category = models.CharField('资产类目', max_length=100)
    item_category = models.CharField('物品分类', max_length=100)
    asset_name = models.CharField('资产名称', max_length=200)
    asset_code = models.CharField(
        '资产编号',
        max_length=100,
        unique=True,
        error_messages={'unique': '资产编号已存在，请使用其他编号'}
    )
    unit = models.CharField('计量单位', max_length=20)
    warning_line = models.IntegerField('警戒线', null=True, blank=True)
    remarks = models.TextField('备注', blank=True, default='')
    attribute_template = models.JSONField('属性模板', default=dict, blank=True)
    asset_count = models.IntegerField('资产数量', default=0)
    in_stock_count = models.IntegerField('在库数量', default=0)
    asset_total_quantity = models.IntegerField('资产总数量', default=0)
    in_stock_quantity = models.IntegerField('在库总数量', default=0)

    class Meta:
        db_table = 'categories_category'
        ordering = ['asset_code']
        verbose_name = '资产类目'
        verbose_name_plural = '资产类目'

    def __str__(self):
        return f'{self.asset_name} ({self.asset_code})'
