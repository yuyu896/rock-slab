# instance-numbering-per-branch: 序列表矩阵化（品目 × 分公司，各自起号）

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0024_clear_instance_sequence"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="instancesequence", name="item"),
        migrations.AddField(
            model_name="instancesequence",
            name="item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="instance_sequences",
                to="categories.category",
                verbose_name="品目",
            ),
        ),
        migrations.AddField(
            model_name="instancesequence",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="instance_sequences",
                to="organizations.branch",
                verbose_name="分公司",
            ),
        ),
        migrations.AddConstraint(
            model_name="instancesequence",
            constraint=models.UniqueConstraint(
                fields=("item", "branch"), name="uniq_instance_seq_item_branch",
            ),
        ),
    ]
