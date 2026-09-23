# 数据迁移（纯 DML）：调拨单已填「调出负责人」的值合并进「经办人」（经办人空才取）。
# 与 0023 删列分离执行，规避 PG 同事务同表 DML+DDL 的 pending trigger events 崩溃。
# 回滚为 noop（字段已删，回滚依赖部署前备份，见 change transfer-responsible-unify design D1）。

from django.db import migrations


def merge_outgoing_responsible_into_handler(apps, schema_editor):
    Transfer = apps.get_model('transfers', 'Transfer')
    for t in Transfer.objects.filter(action_type='transfer', 经办人=''):
        if t.调出负责人:
            t.经办人 = t.调出负责人
            t.save(update_fields=['经办人'])


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0021_rename_采购经办人_transfer_经办人'),
    ]

    operations = [
        migrations.RunPython(merge_outgoing_responsible_into_handler, migrations.RunPython.noop),
    ]
