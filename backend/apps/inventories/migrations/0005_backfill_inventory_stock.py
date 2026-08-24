"""P2 第三刀 DML：存量盘点项按 (任务分公司, 资产编号→品目) 解析换挂台账行。

解析不到的盘点项删除（其盘点记录随 item CASCADE 消失）并输出清理计数——
该类行在台账口径下本不存在，属 Asset 时代的脏数据。
"""
from django.db import migrations


def backfill(apps, schema_editor):
    InventoryItem = apps.get_model('inventories', 'InventoryItem')
    AssetStock = apps.get_model('assets', 'AssetStock')
    Category = apps.get_model('categories', 'Category')

    item_by_code = {c.asset_code: c for c in Category.objects.all()}
    stock_cache = {
        (s.branch_id, s.item_id): s
        for s in AssetStock.objects.all()
    }
    stock_ids = []
    dropped = 0
    for item in InventoryItem.objects.select_related('asset', 'task').iterator():
        asset = item.asset
        branch_id = item.task.branch_id or asset.branch_id
        cat = item_by_code.get(asset.资产编号)
        stock = stock_cache.get((branch_id, cat.id)) if cat else None
        if stock is None:
            item.delete()  # check 随 item CASCADE
            dropped += 1
            continue
        item.stock_id = stock.id
        item.save(update_fields=['stock_id', 'updated_at'])
        stock_ids.append(item.id)

    # 盘点记录的 stock 随其 item 回填
    InventoryCheck = apps.get_model('inventories', 'InventoryCheck')
    for check in InventoryCheck.objects.select_related('item').iterator():
        if check.item.stock_id:
            check.stock_id = check.item.stock_id
            check.save(update_fields=['stock_id', 'updated_at'])

    if dropped:
        print(f'[0005_backfill_inventory_stock] 清理解析不到台账行的盘点项 {dropped} 条（含其盘点记录）')


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('inventories', '0004_inventory_stock_fk_ddl'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
