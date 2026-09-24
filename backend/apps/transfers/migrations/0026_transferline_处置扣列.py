# 结构迁移（纯 DDL）：TransferLine 加「处置扣列」快照（对账重放/离线回退的事实源）。

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0025_transferlineinstance_调拨前编号'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferline',
            name='处置扣列',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='处置扣列快照'),
        ),
    ]
