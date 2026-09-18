# instance-purchase-date-override: 实例个体采购日期覆盖字段

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0027_fixedasset_spec"),
    ]

    operations = [
        migrations.AddField(
            model_name="fixedasset",
            name="采购日期",
            field=models.DateField(blank=True, null=True, verbose_name="采购日期（个体覆盖，空=出生单日期）"),
        ),
    ]
