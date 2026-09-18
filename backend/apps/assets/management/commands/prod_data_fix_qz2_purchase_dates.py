"""生产数据应用（2026-09-18）：泉州二分 7 台实例填采购日期个体覆盖，默认 dry-run。

配套产品变更 purchase-date-override（采购日期两级链：个体覆盖 → 出生单日期）。
本命令仅写覆盖列（记录性字段，不涉台账/单据）；入库日期保持出生快照不动
（前案 qz2_revert 已恢复）。
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
    help = ('生产数据应用：泉州二分 7 台实例填采购日期个体覆盖（两级链生效于'
            '列表/标签/生平/导出）；默认 dry-run，--apply 执行；幂等可重跑')

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
            FixedAsset.objects.filter(内部编号__in=TARGET_DATES).select_related('birth_line__transfer')
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

        self.stdout.write(f'=== {BRANCH_QZ2} 填采购日期个体覆盖（覆盖列当前全空，写入后生效于列表/标签/生平/导出） ===')
        changes = []
        for no, new_date in TARGET_DATES.items():
            inst = insts[no]
            batch_date = inst.birth_line.transfer.调拨日期 if inst.birth_line else None
            mark = '' if inst.采购日期 != new_date else '（已是该值，跳过）'
            self.stdout.write(f'  {no}: 覆盖列 {inst.采购日期 or "空"} → {new_date}（批次日期 {batch_date}）{mark}')
            if inst.采购日期 != new_date:
                changes.append((inst, new_date))
        self.stdout.write(f'  实际写入 {len(changes)} 条；出生单据与入库日期不动')

        if apply:
            with transaction.atomic():
                for inst, new_date in changes:
                    inst.采购日期 = new_date
                    inst.save(update_fields=['采购日期', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：{len(changes)} 条采购日期覆盖'
                ))