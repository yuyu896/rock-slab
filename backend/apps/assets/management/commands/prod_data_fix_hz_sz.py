"""生产数据纠错（2026-09-15 下午）：两案一次性清理，默认 dry-run，--apply 执行。

案1 杭州235公共物资：成对删除全部建账调整单与台账行（81+81）；前置断言该
   分公司无实例、无流转单据；组织节点/节点授权/品目字典保留。
案2 20分苏州：实例档案连完整单据生平整清——涉单 = 行链实例在本分公司 ∪ 出生行，
   含领用/回收等生命周期单据；台账按全部涉单计划聚合净额一次回退（逐单回退会在
   中途产生负值）；发号序列保留。

沿用 prod-data-remediation 能力口径（应用之逆），算量助手复用 0914 命令。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.management.commands.prod_data_fix_20260914 import (
    EFFECTIVE_STATUSES,
    _delete_transfer_with_born_instances,
    _transfer_ledger_plan,
)
from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLineInstance

BRANCH_HZ235 = '杭州235公共物资'
BRANCH_SUZHOU = '20分苏州'


def _aggregate_rollback(plans):
    """全部涉单计划聚合净额一次应用（应用之逆的批量形态）。

    逐单回退会在交织流水（领用在用被回收清零后）中途变负；净额一次应用
    数学上等价于"这些单据从未发生"。任一列净回退为负即抛错回滚。
    """
    net = {}
    for branch, item, column, delta in plans:
        net.setdefault((branch.id, item.id), {})[column] = \
            net.setdefault((branch.id, item.id), {}).get(column, 0) + delta
    for (branch_id, item_id), columns in net.items():
        row = (
            AssetStock.objects.select_for_update()
            .filter(branch_id=branch_id, item_id=item_id).first()
        )
        if row is None and any(columns.values()):
            raise CommandError(f'台账行缺失，无法聚合回退：branch={branch_id} item={item_id}')
        if row is None:
            continue
        changed = False
        for column, delta in columns.items():
            if not delta:
                continue
            current = getattr(row, column) or 0
            if current - delta < 0:
                raise CommandError(
                    f'聚合回退为负：{row.branch.name} × {row.item.asset_code} '
                    f'{column} 当前 {current}，需回退 {delta}'
                )
            setattr(row, column, current - delta)
            changed = True
        if changed:
            row.save(update_fields=['在库数量', '在用数量', '回收库数量', 'updated_at'])


class Command(BaseCommand):
    help = ('生产数据纠错两案（杭州235建账整清/20分苏州实例生平连删）；'
            '默认 dry-run，--apply 执行；案级独立事务，幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        self.case_hz235(apply)
        self.case_suzhou(apply)

        if apply:
            self._recheck_consistency()

    # ------------------------------------------------------------------
    # 案1 杭州235公共物资：调整单建账成对整清
    # ------------------------------------------------------------------

    def case_hz235(self, apply):
        self.stdout.write('')
        self.stdout.write(f'=== 案1 {BRANCH_HZ235}：建账资产整清（调整单+台账行成对删） ===')
        branch = Branch.objects.filter(name=BRANCH_HZ235).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        adjustments = LedgerAdjustment.objects.filter(branch=branch)
        stocks = AssetStock.objects.filter(branch=branch).select_related('item')
        if not adjustments.exists() and not stocks.exists():
            self.stdout.write('无调整单且无台账行，无需处理（幂等跳过）')
            return

        errors = []
        if FixedAsset.objects.filter(branch=branch).exists():
            errors.append('存在实例档案，不适用建账整清路径（改用生平连删路径）')
        n_from = Transfer.objects.filter(from_branch=branch).count()
        n_to = Transfer.objects.filter(to_branch=branch).count()
        if n_from or n_to:
            errors.append(f'存在流转单据（from {n_from} / to {n_to}），不适用建账整清路径')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('案1前置断言失败：' + '；'.join(errors))

        total = sum(r.在库数量 + r.在用数量 + r.回收库数量 for r in stocks)
        self.stdout.write(f'  成对删除：调整单 {adjustments.count()} 张 + 台账行 {stocks.count()} 行（总量 {total}）')
        self.stdout.write('  保留：组织节点、节点授权、品目字典（全局共享）')

        if apply:
            with transaction.atomic():
                n_adj, _ = adjustments.delete()
                n_row, _ = stocks.delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_adj} 调整单 / {n_row} 台账行'
                ))

    # ------------------------------------------------------------------
    # 案2 20分苏州：实例档案连生平单据整清
    # ------------------------------------------------------------------

    def case_suzhou(self, apply):
        self.stdout.write('')
        self.stdout.write(f'=== 案2 {BRANCH_SUZHOU}：实例档案连生平单据整清 ===')
        branch = Branch.objects.filter(name=BRANCH_SUZHOU).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        insts = FixedAsset.objects.filter(branch=branch)
        if not insts.exists():
            self.stdout.write('无实例档案，无需处理（幂等跳过）')
            return

        # 涉单收集：行链实例在本分公司 ∪ 出生行所属单据
        doc_ids = set(
            TransferLineInstance.objects.filter(instance__branch=branch)
            .values_list('line__transfer_id', flat=True)
        )
        doc_ids.update(insts.values_list('birth_line__transfer_id', flat=True))
        doc_ids.discard(None)
        docs = Transfer.objects.filter(id__in=doc_ids).distinct()

        errors = []
        for t in docs.prefetch_related('lines__item__instances', 'lines__instance_links__instance'):
            if t.审批状态 not in EFFECTIVE_STATUSES:
                errors.append(f'生平单据 {t.单据编号} 状态 {t.审批状态} 非生效')
            for line in t.lines.all():
                if line.item.management_type != 'instance':
                    errors.append(
                        f'单据 {t.单据编号} 行 {line.行号}（{line.item.asset_code}）'
                        f'非实例管理品目，整单删除会误伤其数量账'
                    )
                for link in line.instance_links.select_related('instance'):
                    if link.instance.branch_id != branch.id:
                        errors.append(
                            f'单据 {t.单据编号} 行 {line.行号} 链接了他分公司实例 '
                            f'{link.instance.内部编号}，越界中止'
                        )
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('案2前置断言失败：' + '；'.join(errors))

        plans = []
        for t in docs:
            plans.extend(_transfer_ledger_plan(t))
        net = {}
        for b, item, column, delta in plans:
            net.setdefault((b.name, item.asset_code, item.asset_name, column), 0)
            net[(b.name, item.asset_code, item.asset_name, column)] += delta

        self.stdout.write(f'  删除实例 {insts.count()} 个 + 生平单据 {docs.count()} 张：')
        for t in docs.order_by('单据编号'):
            self.stdout.write(f'    {t.单据编号} {t.action_type}/{t.审批状态}')
        self.stdout.write('  台账聚合净额回退：')
        for (bname, code, iname, column), delta in sorted(net.items()):
            self.stdout.write(f'    {bname} {code} {iname} {column} −{delta}')
        self.stdout.write('  保留：数量型/耗材库存、员工、实例发号序列')

        if apply:
            with transaction.atomic():
                doc_ids_str = [str(t.id) for t in docs]
                n_link, _ = TransferLineInstance.objects.filter(instance__branch=branch).delete()
                n_inst, _ = insts.delete()
                n_doc = 0
                for t in docs:
                    _delete_transfer_with_born_instances(t)
                    n_doc += 1
                _aggregate_rollback(plans)
                n_note, _ = Notification.objects.filter(
                    related_object_type='transfer', related_object_id__in=doc_ids_str,
                ).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_doc} 单 / {n_inst} 实例 / {n_link} 关联 / {n_note} 通知'
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
