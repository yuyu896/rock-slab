"""生产数据纠错（2026-09-15）：2分杭州资产整清（合体形态），默认 dry-run，--apply 执行。

单事务内组合两种已验证路径：
  实例侧——出生采购单连删（链接→实例→单据→台账实时算量回退）；
  建账侧——非实例品目调整单与台账行成对删除。
组织节点、员工、品目字典、实例发号序列保留。沿用 prod-data-remediation 能力口径。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.management.commands.prod_data_fix_20260914 import (
    EFFECTIVE_STATUSES,
    _delete_transfer_with_born_instances,
    _rollback_ledger,
    _transfer_ledger_plan,
)
from apps.assets.management.commands.prod_data_fix_20260915 import _assert_in_stock_mirror
from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.categories.models import Category
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine

BRANCH_HZ2 = '2分杭州'
NON_INSTANCE_TYPES = ('quantity', 'consumable')


class Command(BaseCommand):
    help = ('生产数据纠错：2分杭州资产整清（实例出生单连删 + 建账成对删）；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_HZ2).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return

        insts = FixedAsset.objects.filter(branch=branch).select_related('item')
        rows = AssetStock.objects.filter(
            branch=branch, item__management_type__in=NON_INSTANCE_TYPES,
        ).select_related('item')
        adjustments = LedgerAdjustment.objects.filter(
            branch=branch, item__management_type__in=NON_INSTANCE_TYPES,
        )
        if not insts.exists() and not rows.exists() and not adjustments.exists():
            self.stdout.write('无实例且无建账数据，无需处理（幂等跳过）')
            return

        errors = []

        # ---- 实例侧前置：出生单纯实例行、生效、镜像三列 ----
        if insts.filter(birth_line=None).exists():
            errors.append('存在无出生明细行的实例（迁移存量），与整清口径不符')
        birth_lines = TransferLine.objects.filter(born_instances__branch=branch).distinct()
        docs = Transfer.objects.filter(lines__in=birth_lines).distinct()
        for t in docs:
            if t.action_type != 'purchase':
                errors.append(f'出生单据 {t.单据编号} 非采购单（{t.action_type}）')
            if t.审批状态 not in EFFECTIVE_STATUSES:
                errors.append(f'出生单据 {t.单据编号} 状态 {t.审批状态} 非生效')
            for line in t.lines.select_related('item'):
                if line.item.management_type != 'instance':
                    errors.append(
                        f'单据 {t.单据编号} 行 {line.行号}（{line.item.asset_code}）'
                        f'非实例管理品目，整单删除会误伤其数量账'
                    )
        items = Category.objects.filter(instances__branch=branch).distinct()
        _assert_in_stock_mirror(branch, items, errors)

        # ---- 建账侧前置：非实例品目无流转单据行、无错挂实例 ----
        inst_item_ids = list(items.values_list('id', flat=True))
        non_inst_doc_lines = TransferLine.objects.filter(
            transfer__to_branch=branch,
        ).exclude(item_id__in=inst_item_ids).count() + TransferLine.objects.filter(
            transfer__from_branch=branch,
        ).exclude(item_id__in=inst_item_ids).count()
        if non_inst_doc_lines:
            errors.append(f'非实例品目存在流转单据行 {non_inst_doc_lines}，不适用成对删除路径')
        n_mis = FixedAsset.objects.filter(
            branch=branch, item__management_type__in=NON_INSTANCE_TYPES,
        ).count()
        if n_mis:
            errors.append(f'非实例品目上错挂实例档案 {n_mis} 个，需先人工决断')

        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        # ---- 计划输出 ----
        plans = []
        for t in docs:
            plans.extend(_transfer_ledger_plan(t))
        per_item = {}
        for _b, it, _c, delta in plans:
            per_item.setdefault(it.asset_code, [it.asset_name, 0])
            per_item[it.asset_code][1] += delta
        qty_total = sum(r.在库数量 + r.在用数量 + r.回收库数量 for r in rows)

        self.stdout.write(f'=== {BRANCH_HZ2} 资产整清（合体：实例出生单连删 + 建账成对删） ===')
        self.stdout.write(f'  实例侧：删采购单 {docs.count()} 张 + 实例 {insts.count()} 个')
        for code, (name, qty) in sorted(per_item.items()):
            self.stdout.write(f'    {code} {name}：实例与台账在库 −{qty}')
        self.stdout.write(
            f'  建账侧：成对删调整单 {adjustments.count()} 张 + 台账行 {rows.count()} 行（总量 {qty_total}）'
        )
        n_note = Notification.objects.filter(
            related_object_type='transfer',
            related_object_id__in=[str(t.id) for t in docs],
        ).count()
        self.stdout.write(f'  清理关联通知 {n_note} 条')
        self.stdout.write('  保留：组织节点、员工、品目字典、实例发号序列')

        if apply:
            with transaction.atomic():
                doc_ids = [str(t.id) for t in docs]
                n_link = n_inst = n_doc = 0
                for t in docs:
                    l, i, d = _delete_transfer_with_born_instances(t)
                    n_link += l
                    n_inst += i
                    n_doc += d
                _rollback_ledger(plans)
                n_adj, _ = adjustments.delete()
                n_row, _ = rows.delete()
                # 回退只减值不删行：清掉全零行，台账列表不留残行（零行对账中性）
                n_zero, _ = AssetStock.objects.filter(
                    branch=branch, 在库数量=0, 在用数量=0, 回收库数量=0,
                ).delete()
                Notification.objects.filter(
                    related_object_type='transfer', related_object_id__in=doc_ids,
                ).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：实例侧删 {n_doc} 单 / {n_inst} 实例 / {n_link} 关联；'
                    f'建账侧删 {n_adj} 调整单 / {n_row} 台账行；零值残行清理 {n_zero}'
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
