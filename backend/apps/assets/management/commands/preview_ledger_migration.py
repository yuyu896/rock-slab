"""存量迁移预览：暴露脏数据，人工确认后才可执行 migrate_initial_ledger。

输出四部分：
  1. 资产编号不在品目字典的存量行（含相近编号建议）——阻断项
  2. 状态分桶统计（在库/在用/出局）
  3. branch 为空无法定位分公司的存量行——阻断项
  4. 部门文本归一清单（按分公司去重 + 异常行）

注：旧 AssetStock 台账行已在结构迁移（0013）中清空，存量以 Asset 聚合为准
（设计书十一：Asset 是多数路径的事实记录）；旧值差异不再可比。
"""
from django.core.management.base import BaseCommand

from apps.assets.models import Asset
from apps.categories.models import Category
from apps.categories.views import suggest_similar_codes
from apps.organizations.models import Branch


def collect_aggregates():
    """纯 Python 按 (branch, 资产编号, 桶) 聚合（禁数据库特定聚合——前科）。

    返回 (buckets, unregistered, no_branch)：
      buckets: {(branch_id, code): {'在库数量': n, '在用数量': n}}
    """
    branch_map = {b.id: b for b in Branch.objects.all()}
    by_name = {b.name: b for b in Branch.objects.all()}
    registered = set(Category.objects.values_list('asset_code', flat=True))

    buckets = {}
    unregistered = {}
    no_branch = []

    for asset in Asset.objects.all():
        code = (asset.资产编号 or '').strip()
        branch = asset.branch or by_name.get((asset.分公司 or '').strip())
        if branch is None:
            no_branch.append({'序号': asset.序号, '分公司': asset.分公司, '资产编号': code})
            continue
        key = (branch.id, code)
        bucket = buckets.setdefault(key, {'在库数量': 0, '在用数量': 0})
        qty = asset.数量 or 0
        status = asset.当前状态
        if status == '报废':
            continue  # 已出局不入账
        elif status in ('使用中', '维修中'):
            bucket['在用数量'] += qty
        else:  # 在库及其它未知状态保守计入在库
            bucket['在库数量'] += qty
        if code and code not in registered:
            entry = unregistered.setdefault(code, {'数量': 0, '分公司': set(), '建议': None})
            entry['数量'] += qty
            entry['分公司'].add(branch.name)

    for code, entry in unregistered.items():
        entry['分公司'] = sorted(entry['分公司'])
        entry['建议'] = suggest_similar_codes(code)

    return buckets, unregistered, no_branch, branch_map


def collect_departments():
    """扫描 5 处部门文本 → 按分公司归一清单（含异常行）。"""
    from collections import defaultdict
    mapping = defaultdict(set)   # branch name -> {dept}
    anomalies = []

    for asset in Asset.objects.exclude(所属部门='').exclude(所属部门__isnull=True):
        branch_name = asset.分公司 or ''
        if not branch_name:
            anomalies.append({'来源': '资产明细', '分公司': '', '部门': asset.所属部门})
        else:
            mapping[branch_name].add(asset.所属部门.strip())

    from apps.transfers.models import Transfer
    for t in Transfer.objects.all():
        for field in ('调出部门', '调入部门', '需求部门'):
            dept = (getattr(t, field) or '').strip()
            if not dept:
                continue
            branch_name = getattr(t, '调出分公司', '') if field == '调出部门' else (
                getattr(t, '调入分公司', '') if field == '调入部门' else (t.调出分公司 or t.调入分公司 or '')
            )
            if not branch_name:
                anomalies.append({'来源': f'流转单.{field}', '分公司': '', '部门': dept})
            else:
                mapping[branch_name].add(dept)

    return {name: sorted(depts) for name, depts in mapping.items()}, anomalies


class Command(BaseCommand):
    help = '台账存量迁移预览：未登记编号 / 分桶统计 / 无分公司行 / 部门归一清单'

    def handle(self, *args, **options):
        buckets, unregistered, no_branch, branch_map = collect_aggregates()

        self.stdout.write(self.style.MIGRATE_HEADING('== 1. 未登记编号（阻断项，须先补字典或修数据）=='))
        if unregistered:
            for code, info in sorted(unregistered.items()):
                hint = f'，相近：{"、".join(info["建议"])}' if info['建议'] else ''
                self.stdout.write(self.style.WARNING(
                    f'  {code}（数量 {info["数量"]}，分公司：{"、".join(info["分公司"])}）{hint}'
                ))
        else:
            self.stdout.write(self.style.SUCCESS('  无'))

        self.stdout.write(self.style.MIGRATE_HEADING('== 2. 状态分桶统计 =='))
        total_stock = sum(b['在库数量'] for b in buckets.values())
        total_in_use = sum(b['在用数量'] for b in buckets.values())
        self.stdout.write(f'  聚合维度行数：{len(buckets)}（分公司 × 品目）')
        self.stdout.write(f'  在库合计：{total_stock}')
        self.stdout.write(f'  在用合计：{total_in_use}')
        self.stdout.write('  报废（出局，不入账）')

        self.stdout.write(self.style.MIGRATE_HEADING('== 3. 无法定位分公司的存量行（阻断项）=='))
        if no_branch:
            for row in no_branch:
                self.stdout.write(self.style.WARNING(
                    f"  序号 {row['序号']} 资产编号 {row['资产编号']}（分公司字段：{row['分公司'] or '空'}）"
                ))
        else:
            self.stdout.write(self.style.SUCCESS('  无'))

        self.stdout.write(self.style.MIGRATE_HEADING('== 4. 部门归一清单 =='))
        dept_map, anomalies = collect_departments()
        for branch_name, depts in sorted(dept_map.items()):
            self.stdout.write(f'  {branch_name}: {"、".join(depts)}')
        if anomalies:
            self.stdout.write(self.style.WARNING(f'  异常行（分公司为空，需人工判定）{len(anomalies)} 处：'))
            for a in anomalies[:20]:
                self.stdout.write(self.style.WARNING(f"    {a['来源']} 部门「{a['部门']}」"))

        blockers = len(unregistered) + len(no_branch)
        if blockers:
            self.stdout.write(self.style.ERROR(
                f'\n存在 {blockers} 项阻断，migrate_initial_ledger 将拒绝执行；请先补录品目字典/修正数据。'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\n无阻断项，可执行 migrate_initial_ledger（须先完成全量备份）。'))
