"""P2 第三刀：Asset 表物理退役（决策 #4）——字段已按品目/实例/流水三分搬迁，
P1 冻结期验收对账零差异；盘点 FK 已在 inventories 0006 切换到台账行，本表无引用。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0019_align_ledger_to_instances'),
        ('inventories', '0006_drop_inventory_asset_fk'),
    ]

    operations = [
        migrations.DeleteModel(name='Asset'),
    ]
