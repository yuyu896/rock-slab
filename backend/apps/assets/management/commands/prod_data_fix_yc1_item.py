"""生产数据纠错（2026-09-18）：盐城品目整体更正 A-a00008→A-a00011，默认 dry-run，--apply 执行。

员工录错品目（一体机录成笔记本）。四处同批单事务联动（品目维度"应用之逆"）：
出生行 item 更正（流水重算迁移）→ 实例 item+编号换号（序号 1:1）→ 台账存储值
同侧迁移 → 新品目发号行建立。序列号/单价/供应商/单号/日期全保留。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import AssetStock, FixedAsset, InstanceSequence, LedgerAdjustment
from apps.categories.models import Category
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine, TransferLineInstance

BRANCH_YC = '盐城分公司'
FROM_CODE = 'A-a00008'
TO_CODE = 'A-a00011'
EFFECTIVE = ('已通过', '已入库')


class Command(BaseCommand):
    help = ('生产数据纠错：盐城品目整体更正 A-a00008→A-a00011（含换号）；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_YC).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        old_item = Category.objects.filter(asset_code=FROM_CODE).first()
        new_item = Category.objects.filter(asset_code=TO_CODE).first()
        if old_item is None or new_item is None:
            raise CommandError(f'品目缺失：{FROM_CODE}/{TO_CODE}')

        insts = FixedAsset.objects.filter(branch=branch, item=old_item).select_related('item')
        if not insts.exists():
            self.stdout.write(f'{FROM_CODE} 在该分公司无实例，无需处理（幂等跳过）')
            return

        errors = []
        # 目标实例：全在库、有出生行、仅出生链
        for inst in insts:
            if inst.当前状态 != FixedAsset.STATUS_IN_STOCK:
                errors.append(f'{inst.内部编号} 状态 {inst.当前状态}（非在库，存在生平）')
            if inst.birth_line_id is None:
                errors.append(f'{inst.内部编号} 无出生行')
            elif TransferLineInstance.objects.filter(instance=inst).count() != 1:
                errors.append(f'{inst.内部编号} 存在出生链以外的单据行（生平），转人工')
        # 出生行：行账一致、单据生效
        birth_lines = (TransferLine.objects
                       .filter(born_instances__branch=branch, born_instances__item=old_item)
                       .distinct().select_related('transfer', 'item'))
        for ln in birth_lines:
            t = ln.transfer
            if t.action_type != 'purchase':
                errors.append(f'出生单据 {t.单据编号} 非采购单（{t.action_type}）')
            if t.审批状态 not in EFFECTIVE:
                errors.append(f'出生单据 {t.单据编号} 状态 {t.审批状态} 非生效')
            born_n = FixedAsset.objects.filter(birth_line=ln).count()
            if ln.数量 != born_n:
                errors.append(f'行账错位：{t.单据编号} 行{ln.行号} 数量 {ln.数量} != 出生实例 {born_n}')
            if ln.item_id != old_item.id:
                errors.append(f'出生行 {t.单据编号} 行{ln.行号} 品目非 {FROM_CODE}，范围异常')
        # 两品目在该分公司：无调整单、无待审批行、目标品目空白
        if LedgerAdjustment.objects.filter(branch=branch, item__asset_code__in=(FROM_CODE, TO_CODE)).exists():
            errors.append('两品目在该公司存在调整单，流水源残留，不适用整批更正')
        pend = TransferLine.objects.filter(
            transfer__to_branch=branch, transfer__审批状态='待审批',
            item__asset_code__in=(FROM_CODE, TO_CODE),
        ).count()
        if pend:
            errors.append(f'两品目存在待审批单据行 {pend}，先人工处理')
        if FixedAsset.objects.filter(branch=branch, item=new_item).exists():
            errors.append(f'{TO_CODE} 在该公司已有实例（非空白形态），不适用整批更正')
        # 新编号全局无占用
        n = insts.count()
        for inst in insts:
            suffix = inst.内部编号.rsplit('-', 1)[1]
            new_no = f'{TO_CODE}-{branch.code}-{suffix}'
            if FixedAsset.objects.filter(内部编号=new_no).exists():
                errors.append(f'新编号 {new_no} 已被占用')
        # 镜像一致
        row_old = AssetStock.objects.filter(branch=branch, item=old_item).first()
        stock_qty = row_old.在库数量 if row_old else 0
        if stock_qty != insts.filter(当前状态='在库').count():
            errors.append(f'镜像不一致：{FROM_CODE} 台账在库 {stock_qty} vs 实例 {n}')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        self.stdout.write(f'=== {BRANCH_YC} 品目整体更正 {FROM_CODE} → {TO_CODE}（含换号） ===')
        self.stdout.write(f'  出生行更正: {birth_lines.count()} 行（数量合计 {sum(l.数量 for l in birth_lines)}）')
        for inst in insts.order_by('内部编号'):
            suffix = inst.内部编号.rsplit('-', 1)[1]
            self.stdout.write(f'    {inst.内部编号} → {TO_CODE}-{branch.code}-{suffix}（item 更正，序列号/单价保留）')
        self.stdout.write(f'  台账迁移: {FROM_CODE} 在库 {stock_qty}→0（删行）；{TO_CODE} 新建 在库 {n}')
        self.stdout.write(f'  发号行: {TO_CODE}@{BRANCH_YC} last_no={max(int(i.内部编号.rsplit("-", 1)[1]) for i in insts)}；{FROM_CODE} 发号行保留')
        self.stdout.write('  他分公司与其他品目零波及')

        if apply:
            with transaction.atomic():
                for ln in birth_lines:
                    ln.item = new_item
                    ln.save(update_fields=['item', 'updated_at'])
                max_no = 0
                for inst in insts:
                    suffix = int(inst.内部编号.rsplit('-', 1)[1])
                    max_no = max(max_no, suffix)
                    inst.item = new_item
                    inst.内部编号 = f'{TO_CODE}-{branch.code}-{suffix}'
                    inst.save(update_fields=['item', '内部编号', 'updated_at'])
                # 台账同侧迁移
                if row_old is not None:
                    row_old.delete()
                AssetStock.objects.create(branch=branch, item=new_item, 在库数量=n)
                InstanceSequence.objects.update_or_create(
                    item=new_item, branch=branch, defaults={'last_no': max_no},
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：{n} 实例品目+编号更正、{birth_lines.count()} 行更正、台账迁移完成'
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
