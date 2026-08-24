"""P2 第三刀 DDL：盘点项/记录加 stock FK（可空，供回填），纯 DDL。"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0015_ledgeradjustment'),
        ('inventories', '0003_inventorytask_inventories_task_branch_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryitem',
            name='stock',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='inventory_items',
                to='assets.assetstock',
                verbose_name='台账行',
            ),
        ),
        migrations.AddField(
            model_name='inventorycheck',
            name='stock',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='inventory_checks',
                to='assets.assetstock',
                verbose_name='台账行',
            ),
        ),
    ]
