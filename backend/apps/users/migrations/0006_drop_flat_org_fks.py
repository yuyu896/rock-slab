"""组织树正骨：删 User 平铺组织 FK（region / leader / team），员工只挂 branch。

依赖 organizations.0007（其回填逻辑需读取 User.team 历史列，必须先执行）。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_alter_user_role'),
        ('organizations', '0007_branch_team_single_parent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='region',
        ),
        migrations.RemoveField(
            model_name='user',
            name='leader',
        ),
        migrations.RemoveField(
            model_name='user',
            name='team',
        ),
    ]
