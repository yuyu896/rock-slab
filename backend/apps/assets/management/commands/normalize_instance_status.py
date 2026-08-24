"""实例状态归一命令：旧导入时代非法枚举 → 四态（预览 / --confirm）。

背景（P2 第二刀上线后体检）：生产 672 条存量实例仅 6 条合法四态——
「使用中」496（旧 Asset 枚举混入）、「空闲中」168、「维修中」/「已报废」2。
非法状态被对账镜像与列表筛选静默跳过（按「在用」筛不出 496 条），页面功能实际是坏的。

决断路线 A（2026-08-24 与用户确认）：15 个挂实例品目维持数量管理，旧档案为历史死档；
本命令只归一状态枚举修展示/筛选，不动分公司、不动台账、不生成任何单据。
"""
from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.assets.models import FixedAsset
from apps.assets.services.instances import LEGACY_STATUS_MAP, normalize_legacy_status


class Command(BaseCommand):
    help = '实例状态归一：非法枚举（使用中/空闲中/空闲/维修中/已报废）→ 四态（在用/回收库/退役）'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='执行归一（默认仅预览各状态条数与映射）')

    def handle(self, *args, **options):
        stats = list(
            FixedAsset.objects.filter(当前状态__in=LEGACY_STATUS_MAP.keys())
            .order_by()
            .values('当前状态')
            .annotate(n=Count('id'))
        )
        if not stats:
            self.stdout.write(self.style.SUCCESS('全部实例状态均为合法四态，无需归一'))
            return

        for row in stats:
            self.stdout.write(self.style.WARNING(
                f'  {row["当前状态"]} × {row["n"]} → {LEGACY_STATUS_MAP[row["当前状态"]]}'
            ))

        if not options['confirm']:
            self.stdout.write(
                f'共 {sum(r["n"] for r in stats)} 条待归一（预览）。'
                f'确认后执行：python manage.py normalize_instance_status --confirm'
            )
            return

        applied = normalize_legacy_status()
        for old, new, n in applied:
            self.stdout.write(self.style.SUCCESS(f'  {old} × {n} → {new} 完成'))
        self.stdout.write(self.style.SUCCESS(f'归一完成，共 {sum(n for _, _, n in applied)} 条'))
