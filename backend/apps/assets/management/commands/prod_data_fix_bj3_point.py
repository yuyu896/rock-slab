"""生产数据纠错（2026-09-18）：北京三分手动点删（单实例行形态），默认 dry-run，--apply 执行。

点删的单实例行细化：出生行数量归零时删行、单据空行时连单删（含通知）；
台账同额直减、镜像同减。发号序列保留（空号不回收，重新入库不撞号）。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import AssetStock, FixedAsset
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine, TransferLineInstance

BRANCH_BJ3 = '北京三分'
TARGET_NUMBER = 'A-a00011-BJ003-1'
EFFECTIVE = ('已通过', '已入库')


class Command(BaseCommand):
    help = ('生产数据纠错：北京三分手动点删 A-a00011-BJ003-1（归零删行、空行删单）；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_BJ3).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        inst = (
            FixedAsset.objects.select_related('item', 'birth_line__transfer')
            .filter(内部编号=TARGET_NUMBER).first()
        )
        if inst is None:
            self.stdout.write(f'{TARGET_NUMBER} 不存在，无需处理（幂等跳过）')
            return

        errors = []
        if inst.branch_id != branch.id:
            errors.append(f'不属于 {BRANCH_BJ3}（在 {inst.branch.name}）')
        if inst.当前状态 != FixedAsset.STATUS_IN_STOCK:
            errors.append(f'状态 {inst.当前状态}（非在库，存在生平）')
        if inst.birth_line_id is None:
            errors.append('无出生行')
        else:
            if TransferLineInstance.objects.filter(instance=inst).count() != 1:
                errors.append('存在出生链以外的单据行（生平）')
            ln = inst.birth_line
            t = ln.transfer
            if t.action_type != 'purchase':
                errors.append(f'出生单据 {t.单据编号} 非采购单')
            if t.审批状态 not in EFFECTIVE:
                errors.append(f'出生单据 {t.单据编号} 状态 {t.审批状态} 非生效')
            born_n = FixedAsset.objects.filter(birth_line=ln).count()
            if ln.数量 != born_n:
                errors.append(f'行账错位：{t.单据编号} 行{ln.行号} 数量 {ln.数量} != 出生实例 {born_n}')
        row = AssetStock.objects.filter(branch=branch, item=inst.item).first()
        stock_qty = row.在库数量 if row else 0
        n_stock = FixedAsset.objects.filter(
            branch=branch, item=inst.item, 当前状态='在库').count()
        if stock_qty != n_stock:
            errors.append(f'镜像不一致：台账在库 {stock_qty} vs 实例 {n_stock}')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        ln = inst.birth_line
        t = ln.transfer
        qty = ln.数量
        doc_lines = t.lines.count()
        line_will_zero = (qty - 1) == 0
        doc_will_go = line_will_zero and doc_lines == 1
        self.stdout.write(f'=== {BRANCH_BJ3} 手动点删 {TARGET_NUMBER} ===')
        self.stdout.write(f'  实例删除（item={inst.item.asset_code}，台账在库 {stock_qty} → {stock_qty - 1}）')
        if doc_will_go:
            self.stdout.write(f'  单据 {t.单据编号}（单行 ×{qty}）整单删除 + 关联通知清理')
        elif line_will_zero:
            self.stdout.write(f'  {t.单据编号} 行{ln.行号} 数量归零 → 删行（单据其余 {doc_lines - 1} 行保留）')
        else:
            self.stdout.write(f'  {t.单据编号} 行{ln.行号} 数量 {qty} → {qty - 1}')
        self.stdout.write('  发号序列保留（空号不回收，重新入库新号不撞）')

        if apply:
            with transaction.atomic():
                n_note = 0
                if doc_will_go:
                    n_note = Notification.objects.filter(
                        related_object_type='transfer', related_object_id=str(t.id),
                    ).delete()[0]
                TransferLineInstance.objects.filter(instance=inst).delete()
                inst.delete()
                if doc_will_go:
                    t.delete()
                elif line_will_zero:
                    ln.delete()
                else:
                    ln.数量 = qty - 1
                    ln.save(update_fields=['数量', 'updated_at'])
                locked = (
                    AssetStock.objects.select_for_update()
                    .filter(branch=branch, item=inst.item).first()
                )
                if locked is None or locked.在库数量 - 1 < 0:
                    raise CommandError('台账行缺失或回退为负')
                locked.在库数量 = locked.在库数量 - 1
                locked.save(update_fields=['在库数量', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 1 实例，台账在库 −1'
                    + (f'，整单删除 + {n_note} 通知' if doc_will_go else '，行数量联动')
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
