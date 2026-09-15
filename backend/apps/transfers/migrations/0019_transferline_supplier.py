# line-supplier-and-batch-ops: 采购明细行行级供应商

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transfers", "0018_importfingerprint"),
    ]

    operations = [
        migrations.AddField(
            model_name="transferline",
            name="供应商",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="供应商（行级，空=继承单头）"),
        ),
    ]
