# instance-numbering-per-branch 前置：清空旧全局序列行（新结构重建由 makemigrations 生成）

from django.db import migrations


def forward(apps, schema_editor):
    InstanceSequence = apps.get_model('assets', 'InstanceSequence')
    InstanceSequence.objects.all().delete()


def backward(apps, schema_editor):
    pass  # 重编号命令可重建；回滚代码不读此表


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0023_fixedasset_image"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
