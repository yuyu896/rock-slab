"""P2 第三刀 DDL：盘点项/记录删 asset FK、stock 收紧非空、(task, stock) 唯一约束。"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventories', '0005_backfill_inventory_stock'),
    ]

    operations = [
        migrations.RemoveField(model_name='inventoryitem', name='asset'),
        migrations.RemoveField(model_name='inventorycheck', name='asset'),
        migrations.AlterField(
            model_name='inventoryitem',
            name='stock',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='inventory_items',
                to='assets.assetstock',
                verbose_name='台账行',
            ),
        ),
        migrations.AlterField(
            model_name='inventorycheck',
            name='stock',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='inventory_checks',
                to='assets.assetstock',
                verbose_name='台账行',
            ),
        ),
        migrations.AddConstraint(
            model_name='inventoryitem',
            constraint=models.UniqueConstraint(
                fields=('task', 'stock'), name='uniq_inventory_task_stock',
            ),
        ),
    ]
