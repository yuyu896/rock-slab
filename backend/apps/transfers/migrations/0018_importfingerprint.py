# import-dedupe-and-branch-purge: 导入文件防重传指纹表

import uuid

import django.db.models.deletion
from django.db import migrations, models


def _default_uuid():
    return uuid.uuid4()


class Migration(migrations.Migration):

    dependencies = [
        ("transfers", "0017_alter_transfer_回收去向_alter_transfer_领用来源"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportFingerprint",
            fields=[
                ("id", models.UUIDField(default=_default_uuid, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("sha1", models.CharField(max_length=40, verbose_name="文件指纹")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="import_fingerprints", to="users.user", verbose_name="上传者")),
            ],
            options={"verbose_name": "导入指纹", "verbose_name_plural": "导入指纹", "db_table": "transfers_importfingerprint"},
        ),
        migrations.AddConstraint(
            model_name="importfingerprint",
            constraint=models.UniqueConstraint(fields=("user", "sha1"), name="uniq_import_fp_user_sha1"),
        ),
    ]
