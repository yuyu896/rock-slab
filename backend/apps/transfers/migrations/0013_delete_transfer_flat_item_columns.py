"""删除单头品目级平铺列（P2 明细行化，铁律 1：品目信息只在明细行×字典存一份）。"""
from django.db import migrations

FLAT_COLUMNS = [
    '资产编号',
    '资产名称',
    '规格型号',
    '调拨数量',
    '单价',
    '总金额',
    '单位',
    '资产类目',
    '物品分类',
    '存放位置',
    '固定资产内部编号',
]


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0012_backfill_transfer_lines_and_doc_numbers'),
    ]

    operations = [
        migrations.RemoveField(model_name='transfer', name=name)
        for name in FLAT_COLUMNS
    ]
