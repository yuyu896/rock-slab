"""P2 第二刀 DML：历史回收行按 固定资产内部编号 文本回链存活实例。

已物理删除的实例（P1 过渡行为）无从回链，跳过——信息留存于审计日志。
"""
from django.db import migrations


def backfill(apps, schema_editor):
    TransferLine = apps.get_model('transfers', 'TransferLine')
    Link = apps.get_model('transfers', 'TransferLineInstance')
    FixedAsset = apps.get_model('assets', 'FixedAsset')

    instance_by_code = {
        inst.内部编号: inst
        for inst in FixedAsset.objects.only('id', '内部编号').iterator()
    }
    for line in TransferLine.objects.only('id', '固定资产内部编号').iterator():
        code = (line.固定资产内部编号 or '').strip()
        if not code:
            continue
        inst = instance_by_code.get(code)
        if inst is None:
            continue  # 实例已被 P1 过渡回收物理删除
        Link.objects.get_or_create(line_id=line.id, instance_id=inst.id)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('transfers', '0014_assign_source_line_instances'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
