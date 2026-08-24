import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transfers", "0010_transfer_回收去向_transfer_处置方式_transfer_处置金额"),
        # 明细行 FK 跨 app：显式声明建表依赖，保证回滚顺序（organizations.Department / categories.Category）
        ("organizations", "0008_department"),
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransferLine",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("行号", models.IntegerField(verbose_name="行号")),
                ("数量", models.PositiveIntegerField(verbose_name="数量")),
                (
                    "本批规格",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=200,
                        verbose_name="本批规格（记录性）",
                    ),
                ),
                (
                    "单价",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                        verbose_name="单价",
                    ),
                ),
                (
                    "金额",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        verbose_name="金额",
                    ),
                ),
                (
                    "使用人",
                    models.CharField(
                        blank=True, default="", max_length=100, verbose_name="使用人（记录性）"
                    ),
                ),
                (
                    "存放位置",
                    models.CharField(
                        blank=True, default="", max_length=200, verbose_name="存放位置"
                    ),
                ),
                (
                    "固定资产内部编号",
                    models.CharField(
                        blank=True, default="", max_length=100, verbose_name="固定资产内部编号"
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_lines",
                        to="organizations.department",
                        verbose_name="领用部门",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_lines",
                        to="categories.category",
                        verbose_name="品目",
                    ),
                ),
                (
                    "transfer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="transfers.transfer",
                        verbose_name="单头",
                    ),
                ),
            ],
            options={
                "verbose_name": "流转单明细行",
                "verbose_name_plural": "流转单明细行",
                "ordering": ["行号"],
                "db_table": "transfers_transferline",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("transfer", "行号"), name="uniq_transfer_line_no"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="DocumentSequence",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("action_type", models.CharField(db_index=True, max_length=20, verbose_name="单据类型")),
                ("date", models.DateField(verbose_name="日期")),
                ("last_no", models.IntegerField(default=0, verbose_name="已发号数")),
            ],
            options={
                "verbose_name": "单据编号序列",
                "verbose_name_plural": "单据编号序列",
                "db_table": "transfers_documentsequence",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("action_type", "date"), name="uniq_doc_seq_type_date"
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="transfer",
            name="单据编号",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=32,
                null=True,
                unique=True,
                verbose_name="单据编号",
            ),
        ),
    ]
