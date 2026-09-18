"""生产数据纠错（2026-09-18）：北京三分/五分电脑序列号清空，默认 dry-run，--apply 执行。

序列号为记录性字段：不参与台账/镜像/流水不变量；(分公司, 序列号) 唯一约束
豁免空值。清空后列表/导出/盘点自动落"待补录"态，员工经补录/批量维护重录。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import FixedAsset
from apps.organizations.models import Branch

BRANCH_NAMES = ('北京三分', '北京五分')
ITEM_CODES = ('A-a00011',)


class Command(BaseCommand):
    help = ('生产数据纠错：北京三分/五分电脑（A-a00011）序列号清空待重录；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branches = [Branch.objects.filter(name=n).first() for n in BRANCH_NAMES]
        missing_branch = [n for n, b in zip(BRANCH_NAMES, branches) if b is None]
        if missing_branch:
            self.stdout.write(f'分公司不存在，跳过：{missing_branch}')
            return

        targets = FixedAsset.objects.filter(
            branch__in=branches, item__asset_code__in=ITEM_CODES,
        ).exclude(序列号='').select_related('item', 'branch').order_by('branch__code', '内部编号')
        if not targets.exists():
            self.stdout.write('目标范围无非空序列号，无需处理（幂等跳过）')
            return

        self.stdout.write(f'=== {"、".join(BRANCH_NAMES)} × {"、".join(ITEM_CODES)} 序列号清空 ===')
        n_by_branch = {}
        for i in targets:
            n_by_branch[i.branch.name] = n_by_branch.get(i.branch.name, 0) + 1
            self.stdout.write(f'  {i.内部编号} [{i.branch.name}] {i.序列号!r} → \'\'')
        for name, n in n_by_branch.items():
            self.stdout.write(f'  小计 {name}: {n} 台')
        self.stdout.write('  清空后列表/导出/盘点呈"待补录"态；台账/单据/其他字段不动')

        if apply:
            with transaction.atomic():
                n = targets.update(序列号='')  # update() 返回行数（int）
                self.stdout.write(self.style.SUCCESS(f'  已写入：清空 {n} 条序列号'))
            self._recheck_consistency()

    def _recheck_consistency(self):
        from django.core.management import call_command
        from io import StringIO
        self.stdout.write('=== 对账复核（序列号不影响对账，统一健康检查） ===')
        out = StringIO()
        try:
            call_command('check_ledger_consistency', stdout=out)
        except SystemExit:
            self.stdout.write(out.getvalue())
            raise CommandError('对账复验发现差异（见上），请立即核查，必要时用备份还原')
        self.stdout.write(self.style.SUCCESS(out.getvalue().strip()))
