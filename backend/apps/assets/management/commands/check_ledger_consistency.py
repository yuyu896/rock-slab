"""对账命令：台账存储值 == 单据流水重算值（设计书十.3 机器执法）。

流水构成：
  - 期初调整单（is_initial=True，吸收全部历史）
  - 期初时刻之后的已生效流转单（已通过/已入库）
  - 全部非期初调整单

退出码：零差异 0；任何差异 1（供 pytest 与部署检查挂钩）。
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.assets.models import AssetStock, LedgerAdjustment
from apps.transfers.models import Transfer

EFFECTIVE_TRANSFER_STATUSES = ('已通过', '已入库')


class Command(BaseCommand):
    help = '台账对账：逐行逐列比对台账存储值与单据流水重算值'

    def handle(self, *args, **options):
        initial_adjs = LedgerAdjustment.objects.filter(is_initial=True)
        if initial_adjs.exists():
            initial_time = initial_adjs.order_by('created_at').first().created_at
        else:
            initial_time = None

        # 未初始化容忍：无期初单且台账全空 = 期初迁移未执行（P1 首次部署的中间态），
        # 通过并提示；一旦存在期初单或任何台账行，即进入严格对账。
        if initial_time is None and not AssetStock.objects.exists():
            self.stdout.write(self.style.WARNING(
                '台账未初始化（无期初单、无台账行）——请执行 preview_ledger_migration → '
                'migrate_initial_ledger 完成存量入账；初始化后本命令将严格对账'
            ))
            return

        # 期望值累加器：{(branch_id, item_id): {'在库数量': n, ...}}
        expected = {}

        def bump(branch, item, column, delta):
            if branch is None or item is None:
                return
            key = (branch.id, item.id)
            expected.setdefault(key, {'在库数量': 0, '在用数量': 0, '回收库数量': 0})
            expected[key][column] += delta

        from apps.categories.models import Category
        item_map = {c.asset_code: c for c in Category.objects.all()}

        # 调整单（全部：期初 + 非期初）
        for adj in LedgerAdjustment.objects.select_related('branch', 'item'):
            bump(adj.branch, adj.item, adj.目标列, adj.变动量)

        # 生效流转单（期初时刻之后）
        transfers = Transfer.objects.filter(
            审批状态__in=EFFECTIVE_TRANSFER_STATUSES,
        ).select_related('from_branch', 'to_branch')
        if initial_time is not None:
            transfers = transfers.filter(created_at__gte=initial_time)

        for t in transfers:
            item = item_map.get((t.资产编号 or '').strip())
            if item is None:
                continue
            qty = int(t.调拨数量 or 0)
            action = t.action_type
            if action == 'purchase':
                bump(t.to_branch or t.from_branch, item, '在库数量', qty)
            elif action == 'assign':
                bump(t.from_branch, item, '在库数量', -qty)
                bump(t.from_branch, item, '在用数量', qty)
            elif action == 'return':
                branch = t.to_branch or t.from_branch
                bump(branch, item, '在用数量', -qty)
                bump(branch, item, '在库数量', qty)
            elif action == 'transfer':
                bump(t.from_branch, item, '在库数量', -qty)
                bump(t.to_branch, item, '在库数量', qty)
            elif action == 'recovery':
                bump(t.from_branch, item, '在用数量', -qty)
                if getattr(t, '回收去向', 'recycle_bin') == 'recycle_bin':
                    bump(t.from_branch, item, '回收库数量', qty)

        # 逐行比对
        diffs = []
        keys = set(expected) | {(r.branch_id, r.item_id) for r in AssetStock.objects.all()}
        rows = {(r.branch_id, r.item_id): r for r in AssetStock.objects.select_related('branch', 'item')}
        for key in keys:
            row = rows.get(key)
            exp = expected.get(key, {'在库数量': 0, '在用数量': 0, '回收库数量': 0})
            if row is None:
                nonzero = {c: v for c, v in exp.items() if v != 0}
                if nonzero:
                    diffs.append((key, '台账行缺失', nonzero, None))
                continue
            label = f'{row.branch.name} × {row.item.asset_code}'
            for column in ('在库数量', '在用数量', '回收库数量'):
                actual = getattr(row, column)
                if actual != exp[column]:
                    diffs.append((label, column, actual, exp[column]))

        if diffs:
            self.stdout.write(self.style.ERROR(f'台账对账发现 {len(diffs)} 处差异：'))
            for label, column, actual, exp in diffs:
                self.stdout.write(self.style.ERROR(
                    f'  {label} [{column}] 台账值={actual} 期望值={exp}'
                ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS(
            f'台账对账零差异（{len(keys)} 行 × 3 列，流水含 {initial_adjs.count()} 期初单 + '
            f'{transfers.count()} 生效单据 + 非期初调整单）'
        ))
