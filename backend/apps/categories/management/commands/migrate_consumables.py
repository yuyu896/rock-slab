"""存量 B 类品目 → 消耗品迁移（设计书 #2 三档，2026-08-27 修宪）。

默认 dry-run 输出三类清单：
  可迁移（低值易耗品类 × 数量管理 × 在用=0 且 回收库=0）
  需先归零（在用或回收库非零——先经调整单归零/清空再迁）
  实例管理 B 类（供人工决断，不改）
--apply 直改字典属性（management_type），不触碰任何台账数量（铁律 2）；
在用=0 时新旧联动矩阵重放等价，对账前后一致。
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.assets.models import AssetStock
from apps.categories.models import Category


class Command(BaseCommand):
    help = '存量低值易耗品类品目迁移为消耗品（默认 dry-run 预览；--apply 执行；只迁在用=0 且回收库=0）'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']

        b_quant = Category.objects.filter(
            asset_category='低值易耗品类', management_type='quantity',
        ).order_by('asset_code')
        b_inst = Category.objects.filter(
            asset_category='低值易耗品类', management_type='instance',
        ).order_by('asset_code')

        sums = {
            s['item']: s
            for s in AssetStock.objects.values('item').annotate(
                在用=Sum('在用数量'), 回收库=Sum('回收库数量'), 在库=Sum('在库数量'),
            )
        }

        migratable, blocked = [], []
        for cat in b_quant:
            s = sums.get(cat.id) or {'在用': 0, '回收库': 0, '在库': 0}
            if (s['在用'] or 0) == 0 and (s['回收库'] or 0) == 0:
                migratable.append((cat, s['在库'] or 0))
            else:
                blocked.append((cat, s['在用'] or 0, s['回收库'] or 0))

        self.stdout.write(f'可迁移 {len(migratable)} 项（在用/回收库双零，在库保留）：')
        for cat, stock in migratable:
            self.stdout.write(f'  {cat.asset_code} {cat.asset_name}（在库合计 {stock}）')
        self.stdout.write(f'需先归零 {len(blocked)} 项（经调整单归零/清空后再迁）：')
        for cat, in_use, recycle in blocked:
            self.stdout.write(f'  [跳过] {cat.asset_code} {cat.asset_name}（在用 {in_use} / 回收库 {recycle} 非零）')
        self.stdout.write(f'实例管理 B 类 {b_inst.count()} 项（供人工决断，不改）：')
        for cat in b_inst:
            self.stdout.write(f'  [人工] {cat.asset_code} {cat.asset_name}')

        migrated = 0
        if apply:
            pks = [cat.id for cat, _ in migratable]
            for chunk_start in range(0, len(pks), 200):
                Category.objects.filter(pk__in=pks[chunk_start:chunk_start + 200]).update(
                    management_type=Category.MANAGEMENT_CONSUMABLE,
                )
            migrated = len(pks)

        summary = (
            f'迁移 {migrated} 项为消耗品、跳过 {len(blocked)} 项、实例管理 {b_inst.count()} 项'
            + ('（已写入，台账零变动）' if apply else '（dry-run，未写库；确认后加 --apply 执行）')
        )
        self.stdout.write(self.style.SUCCESS(summary))
