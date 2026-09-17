"""生产数据纠错（2026-09-17）：错填在出生行「本批规格」里的供应商归位，默认 dry-run，--apply 执行。

圈定口径（用户 2026-09-17 拍板，只动命中的行）：
  电脑类（品目名称含 电脑/笔记本）：本批规格 精确等于 小熊U租/悟空/易点云/小熊/自购；
  手机类（品目名称含 手机）：本批规格 包含 瑞克/华为/自购 任一。
动作：规格值 → 行级供应商，本批规格清空。行级或单头供应商已有值 → 跳过保护，单独列出。
实例档案两列（规格/供应商）均由出生行派生，行级修正后展示自动归位；数量/台账零变化。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.transfers.models import TransferLine

COMPUTER_KEYWORDS = ('电脑', '笔记本')
COMPUTER_EXACT_SPECS = ('小熊U租', '悟空', '易点云', '小熊', '自购')
PHONE_KEYWORDS = ('手机',)
PHONE_CONTAIN_SPECS = ('瑞克', '华为', '自购')


def _classify(item_name: str) -> str:
    if any(k in (item_name or '') for k in COMPUTER_KEYWORDS):
        return 'computer'
    if any(k in (item_name or '') for k in PHONE_KEYWORDS):
        return 'phone'
    return ''


def _hit(kind: str, spec: str) -> bool:
    if kind == 'computer':
        return spec in COMPUTER_EXACT_SPECS
    if kind == 'phone':
        return any(k in spec for k in PHONE_CONTAIN_SPECS)
    return False


class Command(BaseCommand):
    help = ('生产数据纠错：出生行本批规格错填供应商归位（电脑精确四值/手机包含三关键词）；'
            '默认 dry-run，--apply 执行；供应商已有值跳过保护；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')

        lines = (TransferLine.objects
                 .exclude(本批规格='')
                 .select_related('item', 'transfer'))
        to_fix, protected = [], []
        for line in lines:
            kind = _classify(line.item.asset_name if line.item else '')
            if not _hit(kind, line.本批规格 or ''):
                continue
            if line.供应商 or line.transfer.供应商:
                protected.append(line)
            else:
                to_fix.append(line)

        self.stdout.write(f'命中待改 {len(to_fix)} 行（电脑 {sum(1 for l in to_fix if _classify(l.item.asset_name) == "computer")}'
                          f' / 手机 {sum(1 for l in to_fix if _classify(l.item.asset_name) == "phone")}）'
                          f'；供应商已有值跳过 {len(protected)} 行')
        for line in to_fix:
            self.stdout.write(f'  [待改] {line.transfer.单据编号} 行{line.行号} | {line.item.asset_name} | '
                              f'规格「{line.本批规格}」→ 供应商')
        for line in protected:
            self.stdout.write(f'  [跳过] {line.transfer.单据编号} 行{line.行号} | {line.item.asset_name} | '
                              f'规格「{line.本批规格}」| 既有供应商「{line.供应商 or line.transfer.供应商}」')

        if not apply:
            self.stdout.write('dry-run 结束，未修改任何数据')
            return
        if not to_fix:
            self.stdout.write('无可修改行，结束')
            return

        with transaction.atomic():
            for line in to_fix:
                TransferLine.objects.filter(pk=line.pk).update(
                    供应商=line.本批规格,
                    本批规格='',
                )
        self.stdout.write(f'已修改 {len(to_fix)} 行（本批规格 → 供应商，规格清空）')
