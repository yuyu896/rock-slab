from django.db import models
from core.models import UUIDModel, TimestampedModel


class Category(UUIDModel, TimestampedModel):
    """品目字典（物品户口本）：编号唯一，管理方式为品目固有属性"""
    MANAGEMENT_QUANTITY = 'quantity'
    MANAGEMENT_INSTANCE = 'instance'
    MANAGEMENT_CONSUMABLE = 'consumable'
    MANAGEMENT_CHOICES = [
        (MANAGEMENT_QUANTITY, '数量管理'),
        (MANAGEMENT_INSTANCE, '实例管理'),
        (MANAGEMENT_CONSUMABLE, '消耗品'),
    ]
    # 枚举键 ↔ 中文标签双向映射（导入按 sheet 名定管理方式等处复用，与 choices 同源）
    MANAGEMENT_LABELS = dict(MANAGEMENT_CHOICES)
    MANAGEMENT_CHOICES_LABELS = {label: value for value, label in MANAGEMENT_CHOICES}

    asset_category = models.CharField('资产类目', max_length=100)
    item_category = models.CharField('物品分类', max_length=100)
    asset_name = models.CharField('资产名称', max_length=200)
    asset_code = models.CharField(
        '资产编号',
        max_length=100,
        unique=True,
        error_messages={'unique': '资产编号已存在，请使用其他编号'}
    )
    specification = models.CharField('规格（定义性）', max_length=200, blank=True, default='')
    unit = models.CharField('计量单位', max_length=20)
    management_type = models.CharField(
        '管理方式', max_length=20, choices=MANAGEMENT_CHOICES, default=MANAGEMENT_QUANTITY,
    )
    image = models.ImageField('图片', upload_to='categories/', blank=True, null=True)
    is_rental = models.BooleanField('是否租用', default=False)
    default_supplier = models.CharField('默认供应商（仅预填）', max_length=200, blank=True, default='')
    warning_line = models.IntegerField('默认警戒线', null=True, blank=True)
    remarks = models.TextField('备注', blank=True, default='')
    attribute_template = models.JSONField('属性模板', default=dict, blank=True)

    class Meta:
        db_table = 'categories_category'
        ordering = ['asset_code']
        verbose_name = '资产类目'
        verbose_name_plural = '资产类目'

    def __str__(self):
        return f'{self.asset_name} ({self.asset_code})'
