"""AssetStock V2 重构：一行 = 分公司 × 品目，三存储列。

旧台账行（分公司+资产编号 文本粒度）整体清空——存量以 Asset 表为源、
由期初调整单流程重建（preview_ledger_migration / migrate_initial_ledger，
见 initial-ledger-migration 能力）。此迁移只做结构，不做数据。
"""
from django.db import migrations, models


def clear_legacy_rows(apps, schema_editor):
    AssetStock = apps.get_model('assets', 'AssetStock')
    AssetStock.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0012_assetstock'),
        ('categories', '0004_remove_category_asset_count_and_more'),
    ]

    operations = [
        migrations.RunPython(clear_legacy_rows, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name='assetstock', name='unique_summary_branch_asset_code'),
        migrations.RemoveField(model_name='assetstock', name='分公司'),
        migrations.RemoveField(model_name='assetstock', name='分公司编号'),
        migrations.RemoveField(model_name='assetstock', name='资产编号'),
        migrations.RemoveField(model_name='assetstock', name='资产类目'),
        migrations.RemoveField(model_name='assetstock', name='物品分类'),
        migrations.RemoveField(model_name='assetstock', name='资产名称'),
        migrations.RemoveField(model_name='assetstock', name='规格'),
        migrations.RemoveField(model_name='assetstock', name='数量'),
        migrations.RemoveField(model_name='assetstock', name='是否充足'),
        migrations.AlterField(
            model_name='assetstock',
            name='branch',
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name='ledger_rows',
                to='organizations.branch',
                verbose_name='分公司',
            ),
        ),
        migrations.AddField(
            model_name='assetstock',
            name='item',
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name='ledger_rows',
                to='categories.category',
                verbose_name='品目',
            ),
        ),
        migrations.AddField(model_name='assetstock', name='在库数量', field=models.IntegerField(default=0, verbose_name='在库数量')),
        migrations.AddField(model_name='assetstock', name='在用数量', field=models.IntegerField(default=0, verbose_name='在用数量')),
        migrations.AddField(model_name='assetstock', name='回收库数量', field=models.IntegerField(default=0, verbose_name='回收库数量')),
        migrations.AlterField(
            model_name='assetstock',
            name='警戒线',
            field=models.IntegerField(blank=True, null=True, verbose_name='警戒线（空则用品目默认）'),
        ),
        migrations.AddConstraint(
            model_name='assetstock',
            constraint=models.UniqueConstraint(fields=['branch', 'item'], name='uniq_ledger_branch_item'),
        ),
    ]
