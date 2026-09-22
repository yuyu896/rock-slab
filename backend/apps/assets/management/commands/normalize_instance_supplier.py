"""实例档案供应商存量归一（instance-supplier-dict-select，2026-09-22）：别名合并为字典标准名，默认 dry-run。

口径（用户 2026-09-22 拍板）：
  只改实例个体覆盖值（FixedAsset.供应商），不动出生行/单据（单据纪律）；
  保守映射——只并明确同源别名，拿不准的（'/'、'自购（苹果）' 等）一律不动；
  幂等——归一后重跑无命中。
动作：strip 后精确匹配别名表 → 覆盖为标准名。
"""
from django.core.management.base import BaseCommand

from apps.assets.models import FixedAsset

ALIAS_MAP = {
    '小熊': '小熊U租',
    '小熊u租': '小熊U租',
    '小熊U组': '小熊U租',
}


class Command(BaseCommand):
    help = ('实例档案供应商别名归一（小熊/小熊u租/小熊U组→小熊U租）。'
            '默认 dry-run 只打印影响行数，--apply 执行；只动个体覆盖值，不动出生行。')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认 dry-run）')

    def handle(self, *args, **options):
        apply = options['apply']
        hits = {}
        total = 0
        for inst in FixedAsset.objects.exclude(供应商__isnull=True).exclude(供应商=''):
            std = ALIAS_MAP.get(inst.供应商.strip())
            if std is None:
                continue
            if inst.供应商 != std:
                hits.setdefault(inst.供应商, []).append(inst)
        for alias, insts in hits.items():
            total += len(insts)
            self.stdout.write(f'  「{alias}」→「{ALIAS_MAP[alias.strip()]}」：{len(insts)} 台')
        if not hits:
            self.stdout.write('无别名命中，无需归一。')
            return
        self.stdout.write(f'合计待归一 {total} 台' + ('' if apply else '（dry-run，未写入；加 --apply 执行）'))
        if apply:
            for alias, insts in hits.items():
                for inst in insts:
                    inst.供应商 = ALIAS_MAP[alias.strip()]
                FixedAsset.objects.bulk_update(insts, ['供应商'])
            self.stdout.write(f'已写入 {total} 台（仅个体覆盖值；展示未含出生行派生变化）。')
