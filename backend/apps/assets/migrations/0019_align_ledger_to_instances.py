"""P2 第二刀 DML：台账对齐实例计数——实例管理品目 × 分公司，三列差异生成期初调整单。

方向：以实例计数为准（实例档案是实物盘点过的更细粒度事实）；
branch 为空的存量实例跳过对齐并输出警告清单。
"""
from django.db import migrations

STATE_COLUMN = {'在库': '在库数量', '在用': '在用数量', '回收库': '回收库数量'}


def align(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    FixedAsset = apps.get_model('assets', 'FixedAsset')
    AssetStock = apps.get_model('assets', 'AssetStock')
    LedgerAdjustment = apps.get_model('assets', 'LedgerAdjustment')

    warned = 0
    counts = {}  # (branch_id, item_id) -> {列: n}
    for inst in FixedAsset.objects.exclude(当前状态='退役').iterator():
        if inst.branch_id is None:
            warned += 1
            continue
        key = (inst.branch_id, inst.item_id)
        bucket = counts.setdefault(
            key, {'在库数量': 0, '在用数量': 0, '回收库数量': 0},
        )
        col = STATE_COLUMN.get(inst.当前状态)
        if col:
            bucket[col] += 1

    instance_item_ids = set(
        Category.objects.filter(management_type='instance').values_list('id', flat=True)
    )
    rows = {(r.branch_id, r.item_id): r for r in AssetStock.objects.all()}

    for (branch_id, item_id), bucket in sorted(counts.items()):
        if item_id not in instance_item_ids:
            continue  # 数量管理品目挂实例：不动台账，对账命令出警告交管理员决断
        row = rows.get((branch_id, item_id))
        for column, expected in bucket.items():
            current = getattr(row, column) if row else 0
            delta = expected - current
            if delta == 0:
                continue
            if row is None:
                row = AssetStock(branch_id=branch_id, item_id=item_id)
            setattr(row, column, expected)
            row.save()
            LedgerAdjustment.objects.create(
                branch_id=branch_id,
                item_id=item_id,
                目标列=column,
                变动量=delta,
                事由='实例层接入对齐',
                is_initial=True,
            )

    if warned:
        print(f'[0019_align_ledger_to_instances] 警告：{warned} 条存量实例 branch 为空，'
              f'已跳过台账对齐，请补全分公司归属后人工核对')


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('assets', '0018_instance_reshape_drop_columns'),
    ]

    operations = [
        migrations.RunPython(align, migrations.RunPython.noop),
    ]
