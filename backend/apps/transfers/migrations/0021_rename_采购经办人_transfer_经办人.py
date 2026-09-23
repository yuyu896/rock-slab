# 手写 RenameField：makemigrations 非交互模式退化为 Remove+Add 会丢存量数据

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("transfers", "0020_transfer_created_by_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="transfer",
            old_name="采购经办人",
            new_name="经办人",
        ),
    ]
