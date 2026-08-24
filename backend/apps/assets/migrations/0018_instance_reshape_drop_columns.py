"""P2 第二刀 DDL：item 收紧非空 + 删手抄品目文本列（回填见 0017，铁律 1 不留双存储）。"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0017_instance_reshape_backfill'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fixedasset',
            name='item',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='instances',
                to='categories.category',
                verbose_name='品目',
            ),
        ),
        migrations.RemoveField(model_name='fixedasset', name='资产编号'),
        migrations.RemoveField(model_name='fixedasset', name='资产类目'),
        migrations.RemoveField(model_name='fixedasset', name='资产名称'),
        migrations.RemoveField(model_name='fixedasset', name='供应商'),
        migrations.RemoveField(model_name='fixedasset', name='所属部门'),
        migrations.RemoveField(model_name='fixedasset', name='分公司'),
        migrations.RemoveField(model_name='fixedasset', name='分公司编号'),
        migrations.RemoveField(model_name='fixedasset', name='物品分类'),
        migrations.RemoveField(model_name='fixedasset', name='规格'),
        migrations.RemoveField(model_name='fixedasset', name='是否租用'),
        migrations.RemoveField(model_name='fixedasset', name='数量'),
        migrations.RemoveField(model_name='fixedasset', name='单价'),
        migrations.RemoveField(model_name='fixedasset', name='购入金额'),
        migrations.RemoveField(model_name='fixedasset', name='出库日期'),
    ]
