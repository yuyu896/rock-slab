# instance-level-supplier: 实例个体供应商覆盖字段

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0025_instancesequence_item_branch"),
    ]

    operations = [
        migrations.AddField(
            model_name="fixedasset",
            name="供应商",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="供应商（个体覆盖，空=批次口径）"),
        ),
    ]
