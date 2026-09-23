# 结构迁移（纯 DDL）：删除「调出负责人」字段（值已由 0022 合并进「经办人」）。

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0022_transfer_handler_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transfer',
            name='调出负责人',
        ),
    ]
