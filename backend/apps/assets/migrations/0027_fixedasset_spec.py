# instance-edit-unify-and-spec: 实例个体规格覆盖字段

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0026_fixedasset_supplier"),
    ]

    operations = [
        migrations.AddField(
            model_name="fixedasset",
            name="规格",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="规格（个体覆盖，空=批次口径）"),
        ),
    ]
