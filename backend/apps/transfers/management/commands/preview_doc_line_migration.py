"""迁移前预览：列出存量单据中未登记字典的资产编号（迁移将自动建存根行）。

部署顺序：先跑本命令人工过目 → migrate transfers → check_ledger_consistency。
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '预览流转单明细行迁移：未登记编号清单与影响单据数'

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cur:
                cur.execute('SELECT "资产编号", "资产名称" FROM transfers_transfer')
                rows = cur.fetchall()
        except Exception:
            self.stdout.write(self.style.WARNING(
                '平铺列已不存在（迁移已执行），无需预览'
            ))
            return

        from apps.categories.models import Category
        known = set(Category.objects.values_list('asset_code', flat=True))

        unknown = Counter()
        names = {}
        empty_code = 0
        for code, name in rows:
            code = (code or '').strip()
            if not code:
                empty_code += 1
                continue
            if code not in known:
                unknown[code] += 1
                names[code] = name or ''

        total = len(rows)
        if not unknown and not empty_code:
            self.stdout.write(self.style.SUCCESS(
                f'共 {total} 张存量单据，全部编号已在字典登记，迁移不会创建存根'
            ))
            return

        self.stdout.write(self.style.WARNING(
            f'共 {total} 张存量单据，其中 {sum(unknown.values())} 张的编号未登记字典，'
            '迁移将自动创建以下存根行（单位"件"、类目"未分类"），请事后人工核对：'
        ))
        for code, cnt in sorted(unknown.items()):
            self.stdout.write(f'  {code}（名称：{names[code] or "（空）"}） 影响 {cnt} 张单据')
        if empty_code:
            self.stdout.write(self.style.ERROR(
                f'另有 {empty_code} 张单据资产编号为空，迁移将以 UNK- 前缀建存根，请重点核对'
            ))
