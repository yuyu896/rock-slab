# 数据迁移（纯 DML，与 0026 分离）：存量生效处置行回填扣列快照=旧规则在用×数量。

from django.db import migrations

EFFECTIVE = ('已通过', '已入库')


def backfill(apps, schema_editor):
    Transfer = apps.get_model('transfers', 'Transfer')
    TransferLine = apps.get_model('transfers', 'TransferLine')
    lines = TransferLine.objects.filter(
        transfer__action_type='recovery',
        transfer__回收去向='dispose',
        transfer__审批状态__in=EFFECTIVE,
        处置扣列='',
    ).exclude(数量=0)
    for line in lines.iterator():
        line.处置扣列 = f'在用数量:{line.数量}'
        line.save(update_fields=['处置扣列'])


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0026_transferline_处置扣列'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
