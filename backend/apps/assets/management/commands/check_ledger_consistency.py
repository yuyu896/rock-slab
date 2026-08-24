"""对账命令：台账存储值 == 单据流水重算值，且 实例计数 == 台账列（设计书十.3 机器执法）。

不变量一（数量）：对每「分公司 × 品目」行，以流水重算三列期望值——
  - 期初调整单（is_initial=True，吸收全部历史）
  - 期初时刻之后的已生效流转单（已通过/已入库，按明细行累计，矩阵与 ledger._line_plan 同源）
  - 全部非期初调整单

不变量二（实例）：对每「分公司 × 实例管理品目」，
各状态实例计数 == 台账对应列（退役实例不参与，其减少量由回收去向=直接处置的单据流水解释）。

退出码：零差异 0；任何差异 1（供 pytest 与部署检查挂钩）。
"""
from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.assets.services.ledger import _line_plan
from apps.categories.models import Category
from apps.transfers.models import Transfer

EFFECTIVE_TRANSFER_STATUSES = ('已通过', '已入库')
STATE_COLUMN = {'在库': '在库数量', '在用': '在用数量', '回收库': '回收库数量'}


class Command(BaseCommand):
    help = '台账对账：数量（流水重算）+ 实例（计数镜像）双不变量逐行逐列比对'

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
                '台账未初始化（无期初单、无台账行）——请使用台账增量导入完成期初入账'
                '（差异预览 → 确认生成期初调整单）；初始化后本命令将严格对账'
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

        # 调整单（全部：期初 + 非期初）
        for adj in LedgerAdjustment.objects.select_related('branch', 'item'):
            bump(adj.branch, adj.item, adj.目标列, adj.变动量)

        # 生效流转单（期初时刻之后）：按明细行逐行累计（矩阵与 ledger 服务同源）
        transfers = Transfer.objects.filter(
            审批状态__in=EFFECTIVE_TRANSFER_STATUSES,
        ).select_related('from_branch', 'to_branch').prefetch_related('lines__item')
        if initial_time is not None:
            transfers = transfers.filter(created_at__gte=initial_time)

        for t in transfers:
            for line in t.lines.all():
                for branch, item, column, delta in _line_plan(t, line):
                    bump(branch, item, column, delta)

        # 逐行比对（不变量一）
        diffs = []
        keys = set(expected) | {(r.branch_id, r.item_id) for r in AssetStock.objects.all()}
        rows = {(r.branch_id, r.item_id): r for r in AssetStock.objects.select_related('branch', 'item')}
        for key in keys:
            row = rows.get(key)
            exp = expected.get(key, {'在库数量': 0, '在用数量': 0, '回收库数量': 0})
            if row is None:
                nonzero = {c: v for c, v in exp.items() if v != 0}
                if nonzero:
                    diffs.append((str(key), '台账行缺失', nonzero, None))
                continue
            label = f'{row.branch.name} × {row.item.asset_code}'
            for column in ('在库数量', '在用数量', '回收库数量'):
                actual = getattr(row, column)
                if actual != exp[column]:
                    diffs.append((label, column, actual, exp[column]))

        # 实例计数镜像（不变量二）：实例管理品目 × 分公司
        warnings = []
        instance_item_ids = set(
            Category.objects.filter(management_type='instance').values_list('id', flat=True)
        )
        # .order_by() 清模型默认排序（内部编号），否则排序列混进 GROUP BY/SELECT，
        # 聚合按实例分组、DISTINCT 按实例判重——镜像计数与警告去重双双失效
        inst_counts = (
            FixedAsset.objects.exclude(当前状态='退役')
            .order_by()
            .values('branch_id', 'item_id', '当前状态')
            .annotate(n=Count('id'))
        )
        counted = {}
        for row in inst_counts:
            if row['branch_id'] is None:
                continue  # 分公司未定的存量实例：不计入镜像（迁移警告清单负责）
            if row['item_id'] not in instance_item_ids:
                continue  # 数量管理品目挂实例 → 警告交管理员决断
            key = (row['branch_id'], row['item_id'])
            bucket = counted.setdefault(key, {'在库数量': 0, '在用数量': 0, '回收库数量': 0})
            column = STATE_COLUMN.get(row['当前状态'])
            if column:
                bucket[column] += row['n']

        qty_with_instances = (
            FixedAsset.objects.exclude(item_id__in=instance_item_ids)
            .order_by()
            .values_list('item__asset_code', flat=True).distinct()
        )
        for code in qty_with_instances:
            n = FixedAsset.objects.filter(item__asset_code=code).count()
            warnings.append(
                f'数量管理品目 {code} 挂有 {n} 条实例档案，请决断：改管理方式（改后执行对齐） 或 退役实例'
            )

        orphan_branch = FixedAsset.objects.filter(branch=None).count()
        if orphan_branch:
            warnings.append(f'{orphan_branch} 条实例分公司为空，未参与实例镜像对账，请补全归属')

        for key, bucket in sorted(counted.items()):
            row = rows.get(key)
            label = f'{row.branch.name} × {row.item.asset_code}' if row else str(key)
            for column in ('在库数量', '在用数量', '回收库数量'):
                actual = getattr(row, column) if row else 0
                if actual != bucket[column]:
                    diffs.append((
                        label,
                        f'{column}（实例镜像）',
                        actual,
                        bucket[column],
                    ))

        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING(f'警告：{w}'))

        if diffs:
            self.stdout.write(self.style.ERROR(f'台账对账发现 {len(diffs)} 处差异：'))
            for label, column, actual, exp in diffs:
                self.stdout.write(self.style.ERROR(
                    f'  {label} [{column}] 台账值={actual} 期望值={exp}'
                ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS(
            f'台账对账零差异（{len(keys)} 行 × 3 列 + 实例镜像，流水含 {initial_adjs.count()} 期初单 + '
            f'{transfers.count()} 生效单据 + 非期初调整单）'
        ))
