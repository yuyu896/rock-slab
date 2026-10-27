import apps.assets.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0031_fixedassetassigneechange'),
    ]

    operations = [
        migrations.AddField(
            model_name='fixedasset',
            name='thumbnail',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=apps.assets.models.fixed_asset_thumbnail_upload_to,
                verbose_name='物品缩略图',
            ),
        ),
    ]
