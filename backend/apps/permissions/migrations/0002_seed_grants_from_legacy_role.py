"""数据迁移：按旧 role + region/branch 模型为现有员工种子管理授权。

种子逻辑在 apps.permissions.legacy_seed，便于单测复用。
"""
from django.db import migrations
from apps.permissions.legacy_seed import seed_legacy_grants, reverse_legacy_grants


def seed(apps, schema_editor):
    seed_legacy_grants(apps)


def reverse(apps, schema_editor):
    reverse_legacy_grants(apps)


class Migration(migrations.Migration):

    dependencies = [
        ('permissions', '0001_initial'),
        ('users', '0001_initial'),
        ('organizations', '0004_add_fixedasset_model'),
    ]

    operations = [
        migrations.RunPython(seed, reverse),
    ]
