"""生产数据纠错（2026-09-15）：两案一次性清理，默认 dry-run，--apply 执行。

案A 19分台州 × 工作手机（分公司×品目维度）：删 2 张纯工作手机行出生采购单、
   138 个实例及关联，台账在库同额回退；他分公司同品目数据零波及。
案B 20分苏州 × 实例档案（分公司维度）：删 2 张纯实例行出生采购单、159 个实例
   及关联，对应台账归零；数量型库存/员工/发号序列保留。

沿用 20260914 命令的纠错口径（应用之逆，详见该命令 docstring 与
openspec/specs/prod-data-remediation），助手函数直接复用不复制。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.management.commands.prod_data_fix_20260914 import (
    EFFECTIVE_STATUSES,
    _delete_transfer_with_born_instances,
    _rollback_ledger,
    _transfer_ledger_plan,
)
from apps.assets.models import AssetStock, FixedAsset
from apps.categories.models import Category
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine

BRANCH_TAIZHOU = '19分台州'
ITEM_PHONE = 'A-a00007'
BRANCH_SUZHOU = '20分苏州'


def _assert_in_stock_mirror(branch, items, errors):
    """镜像断言：各品目实例全在库，且台账三列与实例计数一致（在用/回收必为 0）。"""
    for item in items:
        insts = FixedAsset.objects.filter(branch=branch, item=item)
        n_total = insts.count()
        n_stock = insts.filter(当前状态='在库').count()
        if n_total != n_stock:
            errors.append(f'{item.asset_code} 存在非在库实例 {n_total - n_stock} 个，整清会破坏镜像')
        row = AssetStock.objects.filter(branch=branch, item=item).first()
        stock_qty = row.在库数量 if row else 0
        in_use = row.在用数量 if row else 0
        recycle = row.回收库数量 if row else 0
        if in_use or recycle:
            errors.append(f'{item.asset_code} 台账在用/回收库非零（{in_use}/{recycle}），整清会破坏镜像')
        if stock_qty != n_stock:
            errors.append(f'镜像不一致：{item.asset_code} 台账在库 {stock_qty} vs 实例 {n_stock}')


class Command(BaseCommand):
    help = ('生产数据纠错两案（台州工作手机品目清删/苏州实例整清）；'
            '默认 dry-run，--apply 执行；案级独立事务，幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        self.case_taizhou_phone(apply)
        self.case_suzhou(apply)

        if apply:
            self._recheck_consistency()

    # ------------------------------------------------------------------
    # 案A 19分台州 × 工作手机（品目维度）
    # ------------------------------------------------------------------

    def case_taizhou_phone(self, apply):
        self.stdout.write('')
        self.stdout.write(f'=== 案A {BRANCH_TAIZHOU} × 工作手机（{ITEM_PHONE} 品目维度） ===')
        branch = Branch.objects.filter(name=BRANCH_TAIZHOU).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        item = Category.objects.filter(asset_code=ITEM_PHONE).first()
        if item is None:
            raise CommandError(f'品目 {ITEM_PHONE} 不存在')
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
                        f'非 {ITEM_PHONE}），需人工拆行另案处理'
                    )
        _assert_in_stock_mirror(branch, [item], errors)
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('案A前置断言失败：' + '；'.join(errors))

        plans = []
        for t in docs:
            plans.extend(_transfer_ledger_plan(t))
        rollback_qty = sum(delta for _b, _i, _c, delta in plans)
        self.stdout.write(f'  删除采购单 {docs.count()} 张（纯 {item.asset_code} 行）')
        self.stdout.write(f'  实例与台账在库 −{rollback_qty}')
        n_note = Notification.objects.filter(
            related_object_type='transfer',
            related_object_id__in=[str(t.id) for t in docs],
        ).count()
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

    # ------------------------------------------------------------------
    # 案B 20分苏州 × 实例档案（分公司维度，温州模式）
    # ------------------------------------------------------------------

    def case_suzhou(self, apply):
        self.stdout.write('')
        self.stdout.write(f'=== 案B {BRANCH_SUZHOU}：实例档案清空（连出生采购单） ===')
        branch = Branch.objects.filter(name=BRANCH_SUZHOU).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        insts = FixedAsset.objects.filter(branch=branch).select_related('item')
        if not insts.exists():
            self.stdout.write('无实例档案，无需处理（幂等跳过）')
            return

        errors = []
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
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('案B前置断言失败：' + '；'.join(errors))

        plans = []
        for t in docs:
            plans.extend(_transfer_ledger_plan(t))
        per_item = {}
        for _b, it, _c, delta in plans:
            per_item.setdefault(it.asset_code, [it.asset_name, 0])
            per_item[it.asset_code][1] += delta

        self.stdout.write(f'  删除采购单 {docs.count()} 张（纯实例行）')
        for code, (name, qty) in sorted(per_item.items()):
            self.stdout.write(f'    {code} {name}：实例与台账在库 −{qty}')
        self.stdout.write('  保留：数量型/耗材库存及其单据、员工、实例发号序列')
        n_note = Notification.objects.filter(
            related_object_type='transfer',
            related_object_id__in=[str(t.id) for t in docs],
        ).count()
        self.stdout.write(f'  清理关联通知 {n_note} 条')

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
                    f'  已写入：删 {n_doc} 单 / {n_inst} 实例 / {n_link} 关联 / {n_note} 通知，'
                    f'台账回退 {len(plans)} 行次'
                ))

    # ------------------------------------------------------------------

    def _recheck_consistency(self):
        from django.core.management import call_command
        from io import StringIO
        self.stdout.write('')
        self.stdout.write('=== 对账复验 ===')
        out = StringIO()
        try:
            call_command('check_ledger_consistency', stdout=out)
        except SystemExit:
            self.stdout.write(out.getvalue())
            raise CommandError('对账复验发现差异（见上），请立即核查，必要时用备份还原')
        self.stdout.write(self.style.SUCCESS(out.getvalue().strip()))
