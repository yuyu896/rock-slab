"""调拨换号存量补齐（transfer-instance-renumber）。

扫描口径：实例的编号分公司段 ≠ 当前 branch.code，且存在生效调拨单流水
（行-实例关联的调拨单 to_branch=当前分公司）。按空号补位规则换号
（与审批路径同走 _next_no_gap_aware），并回写调拨单行的调拨前编号。
默认预览（只打印不落库）；--confirm 执行；幂等可重跑。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assets.models import FixedAsset
from apps.assets.services.instances import _next_no_gap_aware, renumber_instance
from apps.transfers.models import TransferLineInstance


def _code_branch_segment(code, item_code):
    """按 {品目}-{分公司代码}-{N} 拆编号分公司段；异常格式返回 None。"""
    if not code.startswith(f'{item_code}-'):
        return None
    seg, _, tail = code[len(item_code) + 1:].rpartition('-')
    return seg if seg and tail.isdigit() else None


def _drift_instances():
    """漂号调拨实例：编号分公司段不符 + 存在生效调入流水且未快照前编号。"""
    result = []
    qs = FixedAsset.objects.select_related('item', 'branch').prefetch_related(
        'line_links__line__transfer',
    )
    for inst in qs:
        seg = _code_branch_segment(inst.内部编号, inst.item.asset_code)
        if seg is None or seg == inst.branch.code:
            continue
        for lnk in inst.line_links.all():
            t = lnk.line.transfer
            if (t.action_type == 'transfer'
                    and t.审批状态 in ('已通过', '已入库')
                    and t.to_branch_id == inst.branch_id
                    and not lnk.调拨前编号):
                result.append((inst, lnk))
                break
    return result


class Command(BaseCommand):
    help = ('调拨换号存量补齐：编号分公司段≠当前分公司且有生效调拨流水的实例，'
            '按空号补位规则换号并回写调拨前编号（默认预览，--confirm 执行，幂等）')

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        confirm = options['confirm']
        self.stdout.write(f'模式：{"--confirm 写入" if confirm else "dry-run 预览"}')
        drift = _drift_instances()
        if not drift:
            self.stdout.write('无漂号调拨实例，无需处理（幂等跳过）')
            return

        with transaction.atomic():
            for inst, lnk in drift:
                no = _next_no_gap_aware(inst.item, inst.branch)
                new_code = f'{inst.item.asset_code}-{inst.branch.code}-{no}'
                self.stdout.write(f'  {"写入" if confirm else "预览"} {inst.内部编号} → {new_code}')
                if confirm:
                    old_code = inst.内部编号
                    renumber_instance(inst, new_code)
                    TransferLineInstance.objects.filter(pk=lnk.pk).update(调拨前编号=old_code)
        if confirm:
            self.stdout.write(self.style.SUCCESS(f'已完成 {len(drift)} 台，前编号已回写调拨单行'))
        else:
            self.stdout.write('预览完成（未落库）。加 --confirm 执行')
