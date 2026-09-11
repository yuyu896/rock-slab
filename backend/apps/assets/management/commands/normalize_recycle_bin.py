"""回收库退役归一（recovery-restock-and-ledger）：存量回收库并入在库。

现场管理无回收库概念，回收去向已改直接入库。本命令一次性归一存量：
- 实例：当前状态=回收库 → 在库（清使用人/部门——回收库态本就无使用人，防御性清空）
- 台账：逐分公司×品目，回收库列 N → 在库列 +N（经 ledger.apply_adjustment 留痕）

默认预览（只打印不落库）；--confirm 执行。幂等：全零后重跑报无需归一。
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services import ledger
from apps.users.models import User


class Command(BaseCommand):
    help = '回收库退役归一：存量回收库实例转在库、台账回收库列经调整单并入在库（默认预览，--confirm 执行）'

    def handle(self, *args, **options):
        confirm = options['confirm']
        insts = FixedAsset.objects.filter(当前状态=FixedAsset.STATUS_RECYCLE).order_by('内部编号')
        stocks = list(
            AssetStock.objects.filter(回收库数量__gt=0)
            .select_related('branch', 'item')
            .order_by('branch__name', 'item__asset_code')
        )

        self.stdout.write(f'回收库实例：{insts.count()} 台；台账回收库行：{len(stocks)} 行'
                          f'（合计 {sum(s.回收库数量 for s in stocks)}）')
        for s in stocks:
            self.stdout.write(f'  预览 台账 {s.branch.name} × {s.item.asset_code} '
                              f'回收库 {s.回收库数量} → 在库 +{s.回收库数量}')
        for inst in insts[:20]:
            self.stdout.write(f'  预览 实例 {inst.内部编号} 回收库 → 在库')
        if insts.count() > 20:
            self.stdout.write(f'  ...（其余 {insts.count() - 20} 台略）')

        if not insts.exists() and not stocks:
            self.stdout.write(self.style.SUCCESS('回收库已空，无需归一'))
            return
        if not confirm:
            self.stdout.write(self.style.WARNING('预览完成（未落库）。加 --confirm 执行归一'))
            return

        operator = User.objects.filter(role='admin', status='active').first()
        from apps.assets.services.instances import recycle_bin_to_stock
        with transaction.atomic():
            moved = 0
            for inst in insts:
                recycle_bin_to_stock(inst)
                moved += 1
            adjusted = 0
            for s in stocks:
                n = s.回收库数量
                # 两条留痕：回收库 -N、在库 +N
                ledger.apply_adjustment(
                    branch=s.branch, item=s.item, column=ledger.COLUMN_RECYCLE, delta=-n,
                    reason=f'回收库退役归一：回收库 {n} 并入在库', operator=operator,
                )
                ledger.apply_adjustment(
                    branch=s.branch, item=s.item, column=ledger.COLUMN_STOCK, delta=n,
                    reason=f'回收库退役归一：回收库 {n} 并入在库', operator=operator,
                )
                adjusted += 2

        self.stdout.write(self.style.SUCCESS(
            f'归一完成：实例 {moved} 台转在库，调整单 {adjusted} 条（回收库-在库对半留痕）'))

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='执行归一（默认仅预览）')
