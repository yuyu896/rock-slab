"""管理方式切换对齐命令：实例管理品目的台账列 ↔ 实例计数，差异经调整单收敛。

场景（设计书十一.3 决断路径）：管理员把某品目从数量管理改为实例管理后，
该品目挂有的实例档案开始参与实例镜像对账，但台账数量仍是数量管理时代的事实——
两者不一致会让 check_ledger_consistency / 部署闸门失败。

用法：
  python manage.py align_ledger_to_instances            # 预览差异清单
  python manage.py align_ledger_to_instances --confirm  # 按实例计数对齐（经唯一写入口出调整单）

对齐方向：以实例计数为准（实物档案是更细粒度事实）；退役实例不参与计数。
幂等：无差异时不落任何单；可重复执行。
"""
from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.organizations.models import Branch

STATE_COLUMN = {'在库': '在库数量', '在用': '在用数量', '回收库': '回收库数量'}


def collect_diffs():
    """返回 ([(branch, item, column, 当前台账值, 实例计数)], 分公司为空的实例数)。"""
    instance_items = {
        c.id: c for c in Category.objects.filter(management_type='instance')
    }
    if not instance_items:
        return [], 0

    # .order_by() 清默认排序，防排序列混进 GROUP BY 使聚合按实例细分
    inst_counts = (
        FixedAsset.objects.exclude(当前状态='退役')
        .filter(item_id__in=instance_items)
        .order_by()
        .values('branch_id', 'item_id', '当前状态')
        .annotate(n=Count('id'))
    )
    counted = {}
    orphan = 0
    for row in inst_counts:
        if row['branch_id'] is None:
            orphan += 1
            continue
        key = (row['branch_id'], row['item_id'])
        bucket = counted.setdefault(key, {'在库数量': 0, '在用数量': 0, '回收库数量': 0})
        column = STATE_COLUMN.get(row['当前状态'])
        if column:
            bucket[column] += row['n']

    rows = {
        (r.branch_id, r.item_id): r
        for r in AssetStock.objects.select_related('branch', 'item')
        .filter(item_id__in=instance_items)
    }
    branch_cache = {b.id: b for b in Branch.objects.all()}

    diffs = []
    for key in sorted(set(counted) | set(rows)):
        row = rows.get(key)
        bucket = counted.get(key, {'在库数量': 0, '在用数量': 0, '回收库数量': 0})
        branch = row.branch if row is not None else branch_cache[key[0]]
        item = row.item if row is not None else instance_items[key[1]]
        for column in ('在库数量', '在用数量', '回收库数量'):
            current = getattr(row, column) if row else 0
            if current != bucket[column]:
                diffs.append((branch, item, column, current, bucket[column]))
    return diffs, orphan


class Command(BaseCommand):
    help = '实例管理品目台账对齐：以实例计数为准出调整单（管理方式切换后的决断路径）'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='执行对齐（默认仅预览差异清单）')

    def handle(self, *args, **options):
        diffs, orphan = collect_diffs()

        if orphan:
            self.stdout.write(self.style.WARNING(
                f'警告：{orphan} 条实例分公司为空，不参与对齐，请先补全归属'
            ))

        if not diffs:
            self.stdout.write(self.style.SUCCESS('实例镜像已对齐，无需调整'))
            return

        for branch, item, column, current, target in diffs:
            self.stdout.write(self.style.WARNING(
                f'  {branch.name} × {item.asset_code} [{column}] '
                f'台账={current} → 实例计数={target}（{target - current:+d}）'
            ))

        if not options['confirm']:
            self.stdout.write(
                f'共 {len(diffs)} 处差异（预览）。确认后执行：'
                f'python manage.py align_ledger_to_instances --confirm'
            )
            return

        for branch, item, column, current, target in diffs:
            ledger.apply_adjustment(
                branch, item, column, target - current,
                reason='管理方式切换对齐（以实例计数为准）',
            )
        self.stdout.write(self.style.SUCCESS(
            f'已生成 {len(diffs)} 张调整单完成对齐；请执行 check_ledger_consistency 复核'
        ))
