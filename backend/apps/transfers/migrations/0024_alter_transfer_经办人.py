# 状态对齐（无 DDL）：0021 RenameField 携带的 verbose_name 仍是旧值「采购经办人」，
# 与模型「经办人」存在元数据漂移（makemigrations --check 报警根因），此迁移收口。

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0023_remove_transfer_调出负责人'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='经办人',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='经办人'),
        ),
    ]
