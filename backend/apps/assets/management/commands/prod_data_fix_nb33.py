"""生产数据纠错（2026-09-15）：33分宁波按内部编号点删 3 个实例，默认 dry-run，--apply 执行。

多实例行场景的点删（应用之逆细化到行数量粒度）：
  按出生行分组 → 行数量减去该行被删实例数 → 删行-实例关联与目标实例 →
  台账在库同额直减。流水重算/存储值/实例镜像三处同步，如同该批少购入被删数。
发号序列保留（空号不回收）。沿用 prod-data-remediation 能力口径。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.management.commands.prod_data_fix_20260914 import EFFECTIVE_STATUSES
from apps.assets.models import AssetStock, FixedAsset
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLineInstance

BRANCH_NB33 = '33分宁波'
TARGET_NUMBERS = ('A-a00011-NB033-16', 'A-a00011-NB033-17', 'A-a00011-NB033-19')


class Command(BaseCommand):
    help = ('生产数据纠错：33分宁波按内部编号点删实例（行数量联动）；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_NB33).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return

        insts = list(FixedAsset.objects.filter(内部编号__in=TARGET_NUMBERS).select_related('item'))
        found = {i.内部编号 for i in insts}
        missing = [n for n in TARGET_NUMBERS if n not in found]
        if missing:
            if not insts:
                self.stdout.write(f'目标实例全部不存在，无需处理（幂等跳过）；缺失 {missing}')
                return
            raise CommandError(f'目标实例缺失（部分存在部分缺失，需人工核对）：{missing}')

        errors = []
        for inst in insts:
            if inst.branch_id != branch.id:
                errors.append(f'{inst.内部编号} 不属于 {BRANCH_NB33}（在 {inst.branch.name}）')
            if inst.当前状态 != FixedAsset.STATUS_IN_STOCK:
                errors.append(f'{inst.内部编号} 状态为 {inst.当前状态}（非在库，存在生平）')
            if inst.birth_line_id is None:
                errors.append(f'{inst.内部编号} 无出生行（迁移存量）')

        # 按出生行分组，断言行账一致
        by_line = {}
        for inst in insts:
            by_line.setdefault(inst.birth_line_id, []).append(inst)
        from apps.transfers.models import TransferLine
        lines = {}
        for line_id, group in by_line.items():
            birth_line = TransferLine.objects.select_related('transfer', 'item').get(pk=line_id)
            lines[line_id] = (birth_line, group)
            t = birth_line.transfer
            if t.action_type != 'purchase':
                errors.append(f'出生单据 {t.单据编号} 非采购单（{t.action_type}）')
            if t.审批状态 not in EFFECTIVE_STATUSES:
                errors.append(f'出生单据 {t.单据编号} 状态 {t.审批状态} 非生效')
            born_count = FixedAsset.objects.filter(birth_line=birth_line).count()
            if birth_line.数量 != born_count:
                errors.append(
                    f'行账错位：{t.单据编号} 行{birth_line.行号} 数量 {birth_line.数量} '
                    f'!= 出生实例数 {born_count}，减行不安全'
                )

        # 品目级镜像
        for inst in insts:
            row = AssetStock.objects.filter(branch=branch, item=inst.item).first()
            stock_qty = row.在库数量 if row else 0
            inst_qty = FixedAsset.objects.filter(
                branch=branch, item=inst.item, 当前状态='在库',
            ).count()
            if stock_qty != inst_qty:
                errors.append(
                    f'镜像不一致：{inst.item.asset_code} 台账在库 {stock_qty} vs 实例 {inst_qty}'
                )
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        n_total = len(insts)
        self.stdout.write(f'=== {BRANCH_NB33} 按内部编号点删 {n_total} 个实例 ===')
        row = AssetStock.objects.filter(branch=branch, item=insts[0].item).first()
        for line_id, (birth_line, group) in lines.items():
            names = ', '.join(g.内部编号 for g in group)
            self.stdout.write(
                f'  {birth_line.transfer.单据编号} 行{birth_line.行号}（{birth_line.item.asset_code}）：'
                f'数量 {birth_line.数量} → {birth_line.数量 - len(group)}（删 {names}）'
            )
        self.stdout.write(
            f'  台账在库 {row.在库数量} → {row.在库数量 - n_total}；发号序列保留（空号不回收）'
        )

        if apply:
            with transaction.atomic():
                for line_id, (birth_line, group) in lines.items():
                    birth_line.数量 = birth_line.数量 - len(group)
                    birth_line.save(update_fields=['数量', 'updated_at'])
                TransferLineInstance.objects.filter(instance__in=insts).delete()
                for inst in insts:
                    inst.delete()
                locked = (
                    AssetStock.objects.select_for_update()
                    .filter(branch=branch, item=insts[0].item).first()
                )
                if locked is None or locked.在库数量 - n_total < 0:
                    raise CommandError('台账行缺失或回退为负')
                locked.在库数量 = locked.在库数量 - n_total
                locked.save(update_fields=['在库数量', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_total} 实例，{len(lines)} 行数量联动，台账在库 −{n_total}'
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
