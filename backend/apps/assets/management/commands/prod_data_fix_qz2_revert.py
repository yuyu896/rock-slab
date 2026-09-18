"""生产数据纠错回滚（2026-09-18）：泉州二分 7 实例入库日期恢复出生快照，默认 dry-run。

前案 prod_data_fix_qz2_dates 把"采购日期"诉求误落到入库日期列（采购日期实为
出生单日期的派生值，不存实例）。本命令按 快照不变量（入库日期=出生单调拨日期）
重建 7 个目标实例的入库日期，精确还原前案写入。出生单据全程未动。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import FixedAsset
from apps.organizations.models import Branch

BRANCH_QZ2 = '泉州二分'
TARGET_NUMBERS = (
    'A-a00007-QZ002-36', 'A-a00007-QZ002-37', 'A-a00007-QZ002-38',
    'A-a00007-QZ002-39', 'A-a00007-QZ002-40', 'A-a00007-QZ002-43',
    'A-a00007-QZ002-44',
)


class Command(BaseCommand):
    help = ('生产数据纠错回滚：泉州二分 7 实例入库日期恢复为出生单日期快照'
            '（撤销 qz2_dates 误改）；默认 dry-run，--apply 执行；幂等可重跑')

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

        insts = list(
            FixedAsset.objects.filter(内部编号__in=TARGET_NUMBERS)
            .select_related('birth_line__transfer')
        )
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
                errors.append(f'{inst.内部编号} 不属于 {BRANCH_QZ2}（在 {inst.branch.name}）')
            if inst.birth_line_id is None:
                errors.append(f'{inst.内部编号} 无出生行，无法重建快照')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        self.stdout.write(f'=== {BRANCH_QZ2} 入库日期回滚（恢复出生单日期快照） ===')
        changes = []
        for inst in insts:
            origin = inst.birth_line.transfer.调拨日期
            mark = '' if inst.入库日期 != origin else '（已是快照值，跳过）'
            self.stdout.write(
                f'  {inst.内部编号}: {inst.入库日期} → {origin}'
                f'（出生单 {inst.birth_line.transfer.单据编号}）{mark}'
            )
            if inst.入库日期 != origin:
                changes.append((inst, origin))
        self.stdout.write(f'  实际回滚 {len(changes)} 条；采购日期（出生单派生）全程未动')

        if apply:
            with transaction.atomic():
                for inst, origin in changes:
                    inst.入库日期 = origin
                    inst.save(update_fields=['入库日期', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：回滚 {len(changes)} 条入库日期'
                ))