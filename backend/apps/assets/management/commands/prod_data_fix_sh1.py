"""生产数据纠错（2026-09-16）：上海分公司 × A-a00007 品目维度整清，默认 dry-run，--apply 执行。

复用 prod-data-remediation「品目维度实例档案整清」路径（同 19分台州×工作手机前案）：
按出生实例分公司归属反查出生单（断言纯该品行）→ 镜像断言 → 删关联/实例/单据 →
台账实时算量回退 → 通知清理。发号序列保留；他分公司同品目零波及。
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
from apps.assets.models import FixedAsset
from apps.categories.models import Category
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine

BRANCH_SH1 = '上海分公司'
ITEM_CODE = 'A-a00007'


class Command(BaseCommand):
    help = ('生产数据纠错：上海分公司 A-a00007 品目维度实例整清；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_SH1).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        item = Category.objects.filter(asset_code=ITEM_CODE).first()
        if item is None:
            raise CommandError(f'品目 {ITEM_CODE} 不存在')
        insts = FixedAsset.objects.filter(branch=branch, item=item)
        if not insts.exists():
            self.stdout.write('该分公司该品目无实例，无需处理（幂等跳过）')
            return

        errors = []
        if insts.filter(birth_line=None).exists():
            errors.append('存在无出生明细行的实例（迁移存量），与整清口径不符')
        birth_lines = TransferLine.objects.filter(
            born_instances__branch=branch, born_instances__item=item,
        ).distinct()
        docs = Transfer.objects.filter(lines__in=birth_lines).distinct()
        for t in docs:
            if t.action_type != 'purchase':
                errors.append(f'出生单据 {t.单据编号} 非采购单（{t.action_type}）')
            if t.审批状态 not in EFFECTIVE_STATUSES:
                errors.append(f'出生单据 {t.单据编号} 状态 {t.审批状态} 非生效')
            for line in t.lines.select_related('item'):
                if line.item_id != item.id:
                    errors.append(
                        f'单据 {t.单据编号} 为混行单（行 {line.行号} {line.item.asset_code} '
                        f'非 {ITEM_CODE}），需人工拆行另案处理'
                    )
        _assert_in_stock_mirror(branch, [item], errors)
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        plans = []
        for t in docs:
            plans.extend(_transfer_ledger_plan(t))
        rollback_qty = sum(delta for _b, _i, _c, delta in plans)
        n_note = Notification.objects.filter(
            related_object_type='transfer',
            related_object_id__in=[str(t.id) for t in docs],
        ).count()

        self.stdout.write(f'=== {BRANCH_SH1} × {ITEM_CODE} {item.asset_name}（品目维度） ===')
        self.stdout.write(f'  删除采购单 {docs.count()} 张（纯 {ITEM_CODE} 行）')
        self.stdout.write(f'  实例与台账在库 −{rollback_qty}')
        self.stdout.write(f'  清理关联通知 {n_note} 条；他分公司该品目单据与台账不动')

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
                Notification.objects.filter(
                    related_object_type='transfer', related_object_id__in=doc_ids,
                ).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_doc} 单 / {n_inst} 实例 / {n_link} 关联，'
                    f'台账在库 −{rollback_qty}'
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
