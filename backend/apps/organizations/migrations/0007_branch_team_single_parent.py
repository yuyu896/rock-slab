"""组织树正骨：Branch.team 升唯一父级（必填），删 Branch.region。

回填顺序（纯 Python，禁用数据库特定聚合——SQLite/PG 行为一致）：
1. team 为空的分公司按其员工 team 众数回填（原 assign_branch_team_from_employees 逻辑并入）；
2. 仍为空的分公司挂到其区域的「{区域名}未分组」行政组（get_or_create）；
3. 施加非空约束后删除 Branch.region 列。
"""
import logging
from collections import Counter

from django.db import migrations, models
import django.db.models.deletion

logger = logging.getLogger('org_tree_straighten')


def backfill_branch_team(apps, schema_editor):
    Branch = apps.get_model('organizations', 'Branch')
    Team = apps.get_model('organizations', 'Team')
    Region = apps.get_model('organizations', 'Region')
    User = apps.get_model('users', 'User')

    assigned = []

    # 1) 员工 team 众数回填
    for branch in Branch.objects.filter(team__isnull=True):
        team_ids = list(
            User.objects.filter(branch_id=branch.id, team__isnull=False)
            .values_list('team_id', flat=True)
        )
        if team_ids:
            top_team_id, top_count = Counter(team_ids).most_common(1)[0]
            branch.team_id = top_team_id
            branch.save(update_fields=['team'])
            assigned.append(f'{branch.name}({branch.code}) → 众数组 {top_team_id}（{top_count} 票）')

    # 2) 区域「未分组」兜底组
    for branch in Branch.objects.filter(team__isnull=True):
        region_id = branch.region_id
        if region_id is None:
            # region 列非空，理论不可达；防御性兜底：借用任一已有区域
            region_id = (
                Branch.objects.exclude(region_id=None)
                .values_list('region_id', flat=True).first()
            )
        if region_id is None:
            first_region = Region.objects.first()
            region_id = (
                first_region.id if first_region
                else Region.objects.create(name='默认区域', code='DEF001').id
            )
        region_name = (
            Region.objects.filter(id=region_id).values_list('name', flat=True).first() or ''
        )
        team, _ = Team.objects.get_or_create(
            region_id=region_id,
            name=f'{region_name}未分组',
        )
        branch.team_id = team.id
        branch.save(update_fields=['team'])
        assigned.append(f'{branch.name}({branch.code}) → 兜底组「{team.name}」')

    if assigned:
        logger.info('组织树正骨回填清单：%s', '; '.join(assigned))


def noop_reverse(apps, schema_editor):
    # 数据回填不做逆向恢复（列删除本就依赖备份回滚）
    pass


class Migration(migrations.Migration):

    # PG 限制：同一事务内对 Team 表 INSERT（兜底组）后再 ALTER 其 FK 会报
    # "pending trigger events"（SQLite 走表重建无此限制）。拆事务执行；
    # 回填逻辑幂等，失败重跑安全。
    atomic = False

    dependencies = [
        ('organizations', '0006_company'),
        ('users', '0005_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(backfill_branch_team, noop_reverse),
        migrations.AlterField(
            model_name='branch',
            name='team',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='branches',
                to='organizations.team',
                verbose_name='所属行政组',
            ),
        ),
        migrations.RemoveField(
            model_name='branch',
            name='region',
        ),
    ]
