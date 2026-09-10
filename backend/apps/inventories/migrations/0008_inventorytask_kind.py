# instance-inventory-branch-wide: 盘点方式 kind 显式化 + 存量回填（纯 ORM，SQLite/PG 双兼容）

from django.db import migrations, models


def backfill_kind(apps, schema_editor):
    """回填：department 非空（老实例盘任务）→ instance，其余 → stock。"""
    Task = apps.get_model('inventories', 'InventoryTask')
    Task.objects.filter(department__isnull=False).update(kind='instance')
    Task.objects.filter(department__isnull=True).update(kind='stock')


def unbackfill_kind(apps, schema_editor):
    Task = apps.get_model('inventories', 'InventoryTask')
    Task.objects.update(kind='stock')


class Migration(migrations.Migration):

    dependencies = [
        ("inventories", "0007_inventorytask_department_inventorytask_stock_bin_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventorytask",
            name="kind",
            field=models.CharField(
                blank=True, choices=[("stock", "台账盘点"), ("instance", "实例盘点")],
                default="stock", max_length=20, null=True, verbose_name="盘点方式",
            ),
        ),
        migrations.RunPython(backfill_kind, unbackfill_kind),
        migrations.AlterField(
            model_name="inventorytask",
            name="kind",
            field=models.CharField(
                choices=[("stock", "台账盘点"), ("instance", "实例盘点")],
                default="stock", max_length=20, verbose_name="盘点方式",
            ),
        ),
    ]
