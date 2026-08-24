"""P2 第二刀 DDL：领用来源 + 行-实例关联表 + 明细行实例 M2M（纯 DDL，无 DML，PG 安全）。"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0013_delete_transfer_flat_item_columns'),
        # 行-实例 FK 跨 app：显式声明建表依赖（assets.FixedAsset 自 0004 起存在）
        ('assets', '0004_add_fixedasset_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='transfer',
            name='领用来源',
            field=models.CharField(
                choices=[('stock', '新品库'), ('recycle_bin', '回收库')],
                default='stock',
                max_length=20,
                verbose_name='领用来源',
            ),
        ),
        migrations.CreateModel(
            name='TransferLineInstance',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'line',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='instance_links',
                        to='transfers.transferline',
                        verbose_name='明细行',
                    ),
                ),
                (
                    'instance',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='line_links',
                        to='assets.fixedasset',
                        verbose_name='实例',
                    ),
                ),
            ],
            options={
                'verbose_name': '明细行实例关联',
                'verbose_name_plural': '明细行实例关联',
                'db_table': 'transfers_transferlineinstance',
            },
        ),
        migrations.AddConstraint(
            model_name='transferlineinstance',
            constraint=models.UniqueConstraint(
                fields=('line', 'instance'),
                name='uniq_line_instance',
            ),
        ),
        migrations.AddField(
            model_name='transferline',
            name='instances',
            field=models.ManyToManyField(
                blank=True,
                related_name='transfer_lines',
                through='transfers.TransferLineInstance',
                to='assets.fixedasset',
                verbose_name='关联实例',
            ),
        ),
    ]
