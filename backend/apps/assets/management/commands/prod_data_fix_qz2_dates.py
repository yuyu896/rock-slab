"""生产数据纠错（2026-09-17）：泉州二分按内部编号修正入库日期，默认 dry-run，--apply 执行。

入库日期是出生时从采购单日期落的记录性快照；同单实例共享单据日期，逐实例
不同目标日期只能在实例档案层修正（单据不动）。不涉台账数量与镜像（铁律 2
不介入），对账零影响，末尾对账复核仅作统一健康检查。
"""
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import FixedAsset
from apps.organizations.models import Branch

BRANCH_QZ2 = '泉州二分'
TARGET_DATES = {
    'A-a00007-QZ002-36': datetime.date(2025, 7, 25),
    'A-a00007-QZ002-37': datetime.date(2025, 12, 5),
    'A-a00007-QZ002-38': datetime.date(2025, 7, 7),
    'A-a00007-QZ002-39': datetime.date(2025, 7, 7),
    'A-a00007-QZ002-40': datetime.date(2025, 5, 7),
    'A-a00007-QZ002-43': datetime.date(2025, 1, 6),
    'A-a00007-QZ002-44': datetime.date(2025, 7, 7),
}


class Command(BaseCommand):
    help = ('生产数据纠错：泉州二分按内部编号修正实例入库日期（记录性字段，'
            '不涉台账/单据）；默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_QZ2).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return

        insts = {
            i.内部编号: i for i in
            FixedAsset.objects.filter(内部编号__in=TARGET_DATES).select_related('item')
        }
        missing = [n for n in TARGET_DATES if n not in insts]
        if missing:
            if not insts:
                self.stdout.write(f'目标实例全部不存在，无需处理（幂等跳过）；缺失 {missing}')
                return
            raise CommandError(f'目标实例缺失（部分存在部分缺失，需人工核对）：{missing}')

        errors = []
        for no, inst in insts.items():
            if inst.branch_id != branch.id:
                errors.append(f'{no} 不属于 {BRANCH_QZ2}（在 {inst.branch.name}）')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        self.stdout.write(f'=== {BRANCH_QZ2} 按内部编号修正入库日期 ===')
        changes = []
        for no, new_date in TARGET_DATES.items():
            inst = insts[no]
            mark = '' if inst.入库日期 != new_date else '（幂等空改，跳过）'
            self.stdout.write(f'  {no}: {inst.入库日期} → {new_date}{mark}')
            if inst.入库日期 != new_date:
                changes.append((inst, new_date))
        self.stdout.write(f'  实际更新 {len(changes)} 条；出生单据日期与台账不动')

        if apply:
            with transaction.atomic():
                for inst, new_date in changes:
                    inst.入库日期 = new_date
                    inst.save(update_fields=['入库日期', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：更新 {len(changes)} 条入库日期'
                ))
            self._recheck_consistency()

    def _recheck_consistency(self):
        from django.core.management import call_command
        from io import StringIO
        self.stdout.write('=== 对账复核（统一健康检查，日期不影响对账） ===')
        out = StringIO()
        try:
            call_command('check_ledger_consistency', stdout=out)
        except SystemExit:
            self.stdout.write(out.getvalue())
            raise CommandError('对账复验发现差异（见上），请立即核查，必要时用备份还原')
        self.stdout.write(self.style.SUCCESS(out.getvalue().strip()))
