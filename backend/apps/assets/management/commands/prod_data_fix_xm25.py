"""生产数据纠错（2026-09-15）：25分厦门资产整清，默认 dry-run，--apply 执行。

单事务两块：
  建账侧——调整单与台账行成对删除（117+117）；
  未生效单据侧——全部非生效单据（待审批等）直删，零台账回退
  （未生效单据不参与 check_ledger_consistency 的流水重算）。
组织节点、员工、品目字典保留。沿用 prod-data-remediation 能力口径。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.management.commands.prod_data_fix_20260914 import EFFECTIVE_STATUSES
from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer

BRANCH_XM25 = '25分厦门'


class Command(BaseCommand):
    help = ('生产数据纠错：25分厦门资产整清（建账成对删 + 未生效单据清理）；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_XM25).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return

        rows = AssetStock.objects.filter(branch=branch).select_related('item')
        adjustments = LedgerAdjustment.objects.filter(branch=branch)
        from django.db.models import Q
        pending_docs = Transfer.objects.filter(
            Q(to_branch=branch) | Q(from_branch=branch),
        ).exclude(审批状态__in=EFFECTIVE_STATUSES)

        if not rows.exists() and not adjustments.exists() and not pending_docs.exists():
            self.stdout.write('无台账、无调整单、无未生效单据，无需处理（幂等跳过）')
            return

        errors = []
        n_eff_to = Transfer.objects.filter(to_branch=branch, 审批状态__in=EFFECTIVE_STATUSES).count()
        n_eff_from = Transfer.objects.filter(from_branch=branch, 审批状态__in=EFFECTIVE_STATUSES).count()
        if n_eff_to or n_eff_from:
            errors.append(f'存在生效单据（to {n_eff_to} / from {n_eff_from}），不适用本路径（转生平连删）')
        n_inst = FixedAsset.objects.filter(branch=branch).count()
        if n_inst:
            errors.append(f'存在实例档案 {n_inst} 个，不适用本路径（转出生单/生平连删）')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        total = sum(r.在库数量 + r.在用数量 + r.回收库数量 for r in rows)
        self.stdout.write(f'=== {BRANCH_XM25} 资产整清（建账成对删 + 未生效单据清理） ===')
        self.stdout.write(f'  建账侧：成对删调整单 {adjustments.count()} 张 + 台账行 {rows.count()} 行（总量 {total}）')
        self.stdout.write(f'  未生效侧：直删单据 {pending_docs.count()} 张（零台账回退）')
        n_note = Notification.objects.filter(
            related_object_type='transfer',
            related_object_id__in=[str(t.id) for t in pending_docs],
        ).count()
        self.stdout.write(f'  清理关联通知 {n_note} 条')
        self.stdout.write('  保留：组织节点、员工、品目字典')

        if apply:
            with transaction.atomic():
                # 事务内复查生效状态（防执行瞬间被审批）
                still = pending_docs.filter(审批状态__in=EFFECTIVE_STATUSES).count()
                if still:
                    raise CommandError(f'事务内复查发现 {still} 张单据已变为生效，中止')
                doc_ids = [str(t.id) for t in pending_docs]
                # delete() 返回值含级联子对象（明细行等），先取语义计数
                n_adj = adjustments.count()
                n_row = rows.count()
                n_doc = pending_docs.count()
                adjustments.delete()
                rows.delete()
                pending_docs.delete()
                Notification.objects.filter(
                    related_object_type='transfer', related_object_id__in=doc_ids,
                ).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_adj} 调整单 / {n_row} 台账行 / {n_doc} 未生效单据'
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
