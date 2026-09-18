"""生产数据纠错（2026-09-18）：合肥分公司资产全清（任意单据构成），默认 dry-run，--apply 执行。

三源并存形态（实例出生单含混行 / 调整单+生效数量采购行共建库存 / 待审批单），
此前各路径单独不适用。全清的对账论证：流水重算源（生效单 ∪ 调整单）与存储值
（台账行）同侧归零，镜像两侧同空，待审批单本就不参与重算——无需回退算术。
前置断言：无 from 方向单据、无盘点引用、镜像一致。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.categories.models import Category
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLineInstance

BRANCH_HF1 = '合肥分公司'


class Command(BaseCommand):
    help = ('生产数据纠错：合肥分公司资产全清（任意单据构成，流水与存储同侧归零）；'
            '默认 dry-run，--apply 执行；幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        branch = Branch.objects.filter(name=BRANCH_HF1).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return

        # .order_by() 清模型默认排序：排序字段泄进复合子查询会被 SQLite 拒绝
        docs = (Transfer.objects.filter(to_branch=branch)
                | Transfer.objects.filter(from_branch=branch)).order_by().distinct()
        adjustments = LedgerAdjustment.objects.filter(branch=branch)
        rows = AssetStock.objects.filter(branch=branch).select_related('item')
        insts = FixedAsset.objects.filter(branch=branch)
        if not docs.exists() and not adjustments.exists() \
                and not rows.exists() and not insts.exists():
            self.stdout.write('无单据、无调整单、无台账行、无实例，无需处理（幂等跳过）')
            return

        errors = []
        n_from = Transfer.objects.filter(from_branch=branch).count()
        if n_from:
            errors.append(f'存在本司为调出方的单据 {n_from} 张（他司数据耦合），中止全清')
        from apps.inventories.models import InventoryTask, InventoryItem, InventoryCheck
        n_task = InventoryTask.objects.filter(branch=branch).count()
        n_inv = (InventoryItem.objects.filter(stock__branch=branch).count()
                 + InventoryCheck.objects.filter(stock__branch=branch).count())
        if n_task or n_inv:
            errors.append(f'存在盘点引用（任务 {n_task} / 明细核查 {n_inv}），中止全清')
        for item in Category.objects.filter(instances__branch=branch).distinct():
            r = AssetStock.objects.filter(branch=branch, item=item).first()
            sq = r.在库数量 if r else 0
            iq = FixedAsset.objects.filter(
                branch=branch, item=item, 当前状态='在库').count()
            if sq != iq:
                errors.append(f'镜像不一致：{item.asset_code} 台账在库 {sq} vs 实例 {iq}')
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('前置断言失败：' + '；'.join(errors))

        eff = docs.filter(审批状态__in=('已通过', '已入库'))
        pending = docs.exclude(审批状态__in=('已通过', '已入库'))
        n_note = Notification.objects.filter(
            related_object_type='transfer',
            related_object_id__in=[str(t.id) for t in docs],
        ).count()
        qty_total = sum(r.在库数量 + r.在用数量 + r.回收库数量 for r in rows)

        self.stdout.write(f'=== {BRANCH_HF1} 资产全清（流水与存储同侧归零） ===')
        self.stdout.write(f'  删单据 {docs.count()} 张（生效 {eff.count()} / 其他 {pending.count()}，含待审批与混行单）')
        self.stdout.write(f'  删调整单 {adjustments.count()} 张 + 台账行 {rows.count()} 行（非实例总量 {qty_total}）')
        self.stdout.write(f'  删实例 {insts.count()} 个及行-实例关联')
        self.stdout.write(f'  清理关联通知 {n_note} 条')
        self.stdout.write('  保留：组织节点、员工、部门字典、品目字典、实例发号序列')

        if apply:
            with transaction.atomic():
                doc_ids = [str(t.id) for t in docs]
                # 语义计数先取后删（delete() 返回含级联明细行）
                n_doc = docs.count()
                n_adj = adjustments.count()
                n_row = rows.count()
                n_inst = insts.count()
                TransferLineInstance.objects.filter(instance__branch=branch).delete()
                insts.delete()
                docs.delete()
                adjustments.delete()
                rows.delete()
                Notification.objects.filter(
                    related_object_type='transfer', related_object_id__in=doc_ids,
                ).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_doc} 单 / {n_adj} 调整单 / {n_row} 台账行 / '
                    f'{n_inst} 实例 / {n_note} 通知'
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
