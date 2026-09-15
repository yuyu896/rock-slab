"""生产数据纠错（2026-09-15）：32分宁波非实例品目建账整清，默认 dry-run，--apply 执行。

删除：非实例管理品目（quantity/consumable）的台账行与建账调整单，成对同删。
保留：实例品目的台账行/调整单/实例档案（实例品目调整单是镜像解释源）、
组织节点、品目字典。前置断言：无流转单据、非实例品目上无实例档案。

沿用 prod-data-remediation 能力口径（成对删除的对账自洽论证同杭州235 案）。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.organizations.models import Branch
from apps.transfers.models import Transfer

BRANCH_NB32 = '32分宁波'
NON_INSTANCE_TYPES = ('quantity', 'consumable')


class Command(BaseCommand):
    help = ('生产数据纠错：32分宁波非实例品目建账整清（实例档案保留）；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_NB32).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return

        rows = AssetStock.objects.filter(
            branch=branch, item__management_type__in=NON_INSTANCE_TYPES,
        ).select_related('item')
        adjustments = LedgerAdjustment.objects.filter(
            branch=branch, item__management_type__in=NON_INSTANCE_TYPES,
        )
        if not rows.exists() and not adjustments.exists():
            self.stdout.write('非实例品目无台账行且无调整单，无需处理（幂等跳过）')
            return

        errors = []
        n_from = Transfer.objects.filter(from_branch=branch).count()
        n_to = Transfer.objects.filter(to_branch=branch).count()
        if n_from or n_to:
            errors.append(f'存在流转单据（from {n_from} / to {n_to}），不适用建账整清路径')
        n_mis_inst = FixedAsset.objects.filter(
            branch=branch, item__management_type__in=NON_INSTANCE_TYPES,
        ).count()
        if n_mis_inst:
            errors.append(f'非实例品目上错挂实例档案 {n_mis_inst} 个，需先人工决断')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        keep_rows = AssetStock.objects.filter(
            branch=branch, item__management_type='instance',
        ).select_related('item')
        keep_inst = FixedAsset.objects.filter(branch=branch)
        total = sum(r.在库数量 + r.在用数量 + r.回收库数量 for r in rows)
        self.stdout.write(f'=== {BRANCH_NB32} 非实例品目建账整清 ===')
        self.stdout.write(f'  成对删除：调整单 {adjustments.count()} 张 + 台账行 {rows.count()} 行（总量 {total}）')
        for r in rows.order_by('item__asset_code'):
            self.stdout.write(
                f'    {r.item.asset_code} {r.item.asset_name}({r.item.management_type}): '
                f'在库{r.在库数量}/在用{r.在用数量}/回收{r.回收库数量}'
            )
        self.stdout.write('  保留：实例品目台账行 %d 行、实例品目调整单 %d 张、实例档案 %d 个' % (
            keep_rows.count(),
            LedgerAdjustment.objects.filter(
                branch=branch, item__management_type='instance').count(),
            keep_inst.count(),
        ))

        if apply:
            with transaction.atomic():
                n_adj, _ = adjustments.delete()
                n_row, _ = rows.delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_adj} 调整单 / {n_row} 台账行'
                ))
            self._recheck_consistency()

    def _recheck_consistency(self):
        from django.core.management import call_command
        from io import StringIO
        self.stdout.write('=== 对账复验 ===')
        out = StringIO()
        try:
            call_command('check_ledger_consistency', stdout=out)
        except SystemExit:
            self.stdout.write(out.getvalue())
            raise CommandError('对账复验发现差异（见上），请立即核查，必要时用备份还原')
        self.stdout.write(self.style.SUCCESS(out.getvalue().strip()))
