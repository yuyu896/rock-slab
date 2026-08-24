"""P2 第二刀 DDL：FixedAsset 加列（item/birth_line/department，先可空供回填）+ 实例编号序列表（纯 DDL）。"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0015_ledgeradjustment'),
        ('categories', '0001_initial'),
        ('organizations', '0008_department'),
        ('transfers', '0011_transferline_documentsequence_transfer_单据编号'),
    ]

    operations = [
        migrations.AddField(
            model_name='fixedasset',
            name='item',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='instances',
                to='categories.category',
                verbose_name='品目',
            ),
        ),
        migrations.AddField(
            model_name='fixedasset',
            name='birth_line',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='born_instances',
                to='transfers.transferline',
                verbose_name='出生明细行',
            ),
        ),
        migrations.AddField(
            model_name='fixedasset',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='instances',
                to='organizations.department',
                verbose_name='归属部门',
            ),
        ),
        migrations.AlterField(
            model_name='fixedasset',
            name='当前状态',
            field=models.CharField(
                choices=[
                    ('在库', '在库'),
                    ('在用', '在用'),
                    ('回收库', '回收库'),
                    ('退役', '退役'),
                ],
                db_index=True,
                default='在库',
                max_length=20,
                verbose_name='当前状态',
            ),
        ),
        migrations.AlterField(
            model_name='fixedasset',
            name='使用人',
            field=models.CharField(
                blank=True, default='', max_length=100,
                verbose_name='使用人（记录性）',
            ),
        ),
        migrations.AlterField(
            model_name='fixedasset',
            name='序列号',
            field=models.CharField(
                blank=True, default='', max_length=200,
                verbose_name='序列号（空=待补录）',
            ),
        ),
        migrations.CreateModel(
            name='InstanceSequence',
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
                ('last_no', models.IntegerField(default=0, verbose_name='已发号数')),
                (
                    'item',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='instance_sequence',
                        to='categories.category',
                        verbose_name='品目',
                    ),
                ),
            ],
            options={
                'verbose_name': '实例编号序列',
                'verbose_name_plural': '实例编号序列',
                'db_table': 'assets_instancesequence',
            },
        ),
    ]
