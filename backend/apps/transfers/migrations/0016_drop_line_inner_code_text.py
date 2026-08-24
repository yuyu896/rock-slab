"""P2 第二刀 DDL：删明细行 固定资产内部编号 文本列（实例引用取代，DML 回链见 0015）。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0015_backfill_line_instances'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transferline',
            name='固定资产内部编号',
        ),
    ]
