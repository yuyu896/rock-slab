"""Delete two confirmed test assets from Yangzhou; dry-run unless --apply is passed."""
from decimal import Decimal
from io import StringIO

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import AssetStock, FixedAsset, InstanceSequence
from apps.assets.services.instances import next_available_instance_number
from apps.inventories.models import InventoryInstanceItem
from apps.notifications.models import ApprovalCC, Notification
from apps.organizations.models import Branch
from apps.transfers.models import TransferLineInstance

BRANCH_CODE = 'YZ001'
EFFECTIVE_STATUSES = ('已通过', '已入库')
TARGETS = {
    'A-a00001-YZ001-1': {
        'item_code': 'A-a00001',
        'purchase_doc': 'CG20260916-007',
        'line_quantity': 1,
        'document_line_count': 1,
    },
    'A-a00007-YZ001-42': {
        'item_code': 'A-a00007',
        'purchase_doc': 'CG20251007-002',
        'line_quantity': 42,
        'document_line_count': 7,
    },
}
CENT = Decimal('0.01')


class Command(BaseCommand):
    help = 'Delete the two confirmed Yangzhou test assets; dry-run by default.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Apply the deletion transaction')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f"模式：{'--apply 写入' if apply else 'dry-run 预览'}")
        if apply:
            self.stdout.write('请先确认已完成生产数据库即时备份。')

        plans = self._build_plans()
        if plans is None:
            return
        self._print_plans(plans)
        if not apply:
            return

        with transaction.atomic():
            self._lock_target_rows()
            plans = self._build_plans()
            if plans is None:
                return
            self._apply_plans(plans)
            self._recheck_consistency()

    def _build_plans(self):
        branch = Branch.objects.filter(code=BRANCH_CODE).first()
        if branch is None:
            raise CommandError(f'找不到分公司代码 {BRANCH_CODE}')

        instances = list(
            FixedAsset.objects.select_related('item', 'branch', 'birth_line__transfer')
            .filter(内部编号__in=TARGETS)
        )
        found = {inst.内部编号 for inst in instances}
        missing = set(TARGETS) - found
        if missing:
            if not instances:
                self.stdout.write(f'目标资产均已不存在，跳过：{", ".join(sorted(missing))}')
                return None
            raise CommandError(f'只找到部分目标资产，停止以免部分处理：{", ".join(sorted(missing))}')

        target_ids_by_item = {}
        for instance in instances:
            target_ids_by_item.setdefault(instance.item_id, []).append(instance.pk)

        errors = []
        plans = []
        for inst in instances:
            expected = TARGETS[inst.内部编号]
            if inst.branch_id != branch.id:
                errors.append(f'{inst.内部编号} 不属于分公司代码 {BRANCH_CODE}')
            if inst.当前状态 != FixedAsset.STATUS_IN_STOCK:
                errors.append(f'{inst.内部编号} 状态为 {inst.当前状态}，不是在库')
            if inst.item.asset_code != expected['item_code']:
                errors.append(f'{inst.内部编号} 品目编号为 {inst.item.asset_code}，与预期不符')
            if inst.item.management_type != 'instance':
                errors.append(f'{inst.内部编号} 品目不是实例管理')
            if inst.birth_line_id is None:
                errors.append(f'{inst.内部编号} 没有采购出生明细')
                continue

            line = inst.birth_line
            transfer = line.transfer
            if transfer.action_type != 'purchase':
                errors.append(f'{inst.内部编号} 出生单据不是采购入库')
            if transfer.单据编号 != expected['purchase_doc']:
                errors.append(f'{inst.内部编号} 出生单据为 {transfer.单据编号}，与预期不符')
            if transfer.审批状态 not in EFFECTIVE_STATUSES:
                errors.append(f'{transfer.单据编号} 状态 {transfer.审批状态} 尚未生效')
            if line.item_id != inst.item_id:
                errors.append(f'{inst.内部编号} 与出生明细品目不一致')
            if line.数量 != expected['line_quantity']:
                errors.append(
                    f'{transfer.单据编号} 行数量为 {line.数量}，预期 {expected["line_quantity"]}'
                )
            if transfer.lines.count() != expected['document_line_count']:
                errors.append(
                    f'{transfer.单据编号} 明细行数为 {transfer.lines.count()}，'
                    f'预期 {expected["document_line_count"]}'
                )

            born_instance_ids = set(
                FixedAsset.objects.filter(birth_line=line).values_list('pk', flat=True)
            )
            linked_instance_ids = set(
                TransferLineInstance.objects.filter(line=line).values_list('instance_id', flat=True)
            )
            target_links = list(
                TransferLineInstance.objects.filter(instance=inst).select_related('line')
            )
            if len(born_instance_ids) != line.数量 or len(linked_instance_ids) != line.数量:
                errors.append(
                    f'{transfer.单据编号} 行{line.行号} 数量、出生实例和行关联不一致：'
                    f'{line.数量}/{len(born_instance_ids)}/{len(linked_instance_ids)}'
                )
            if born_instance_ids != linked_instance_ids:
                errors.append(
                    f'{transfer.单据编号} 行{line.行号} 出生实例与明细关联并非相同资产集合'
                )
            if len(target_links) != 1 or target_links[0].line_id != line.id:
                errors.append(f'{inst.内部编号} 存在出生采购单以外的单据关联')
            if InventoryInstanceItem.objects.filter(instance=inst).exists():
                errors.append(f'{inst.内部编号} 已有盘点记录，停止删除以保留盘点历史')
            reconciliation_history = self._reconciliation_history(inst.pk)

            stock = AssetStock.objects.filter(branch=branch, item=inst.item).first()
            instance_stock = FixedAsset.objects.filter(
                branch=branch, item=inst.item, 当前状态=FixedAsset.STATUS_IN_STOCK,
            ).count()
            if stock is None or stock.在库数量 != instance_stock:
                actual_stock = stock.在库数量 if stock else None
                errors.append(
                    f'{inst.item.asset_code} 台账在库 {actual_stock} 与在库实例 {instance_stock} 不一致'
                )

            remaining_quantity = line.数量 - 1
            document_will_delete = remaining_quantity == 0 and transfer.lines.count() == 1
            amount_after = line.金额
            if remaining_quantity > 0 and line.金额 is not None:
                if line.单价 is None:
                    errors.append(f'{transfer.单据编号} 行{line.行号} 有金额但无单价，无法安全调整金额')
                else:
                    expected_amount = (line.单价 * line.数量).quantize(CENT)
                    if line.金额 != expected_amount:
                        errors.append(
                            f'{transfer.单据编号} 行{line.行号} 金额 {line.金额} '
                            f'不是单价×数量 {expected_amount}，需要人工核对'
                        )
                    else:
                        amount_after = (line.单价 * remaining_quantity).quantize(CENT)

            next_serial = next_available_instance_number(
                inst.item,
                branch,
                target_ids_by_item[inst.item_id],
            )
            plans.append({
                'instance': inst,
                'line': line,
                'transfer': transfer,
                'stock_before': stock.在库数量 if stock else None,
                'remaining_quantity': remaining_quantity,
                'document_will_delete': document_will_delete,
                'amount_after': amount_after,
                'notification_count': Notification.objects.filter(
                    related_object_type='transfer', related_object_id=str(transfer.id),
                ).count() if document_will_delete else 0,
                'approval_cc_count': ApprovalCC.objects.filter(
                    transfer=transfer,
                ).count() if document_will_delete else 0,
                'reconciliation_history': reconciliation_history,
                'sequence_last_no': InstanceSequence.objects.filter(
                    item=inst.item, branch=branch,
                ).values_list('last_no', flat=True).first(),
                'next_internal_code': f'{inst.item.asset_code}-{branch.code}-{next_serial}',
            })

        if errors:
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  [前置检查失败] {error}'))
            raise CommandError('生产数据与预期不一致，未执行任何修改')

        return plans

    @staticmethod
    def _reconciliation_history(instance_id):
        if not apps.is_installed('apps.reconciliation'):
            return []
        comparison = apps.get_model('reconciliation', 'ReconciliationComparison')
        return list(comparison.objects.filter(system_instance_id=instance_id))

    @staticmethod
    def _lock_target_rows():
        targets = list(
            FixedAsset.objects.filter(内部编号__in=TARGETS)
            .values('pk', 'branch_id', 'item_id')
        )
        stock_keys = sorted({
            (row['branch_id'], row['item_id'])
            for row in targets if row['branch_id'] is not None
        })
        for branch_id, item_id in stock_keys:
            AssetStock.objects.select_for_update().filter(
                branch_id=branch_id, item_id=item_id,
            ).first()
        ids = sorted(row['pk'] for row in targets)
        list(
            FixedAsset.objects.select_for_update()
            .filter(pk__in=ids).order_by('pk').values_list('pk', flat=True)
        )
        for branch_id, item_id in stock_keys:
            InstanceSequence.objects.select_for_update().filter(
                branch_id=branch_id, item_id=item_id,
            ).first()

    def _print_plans(self, plans):
        self.stdout.write(f'=== 扬州分公司 {len(plans)} 条资产删除预览 ===')
        for plan in plans:
            inst = plan['instance']
            line = plan['line']
            transfer = plan['transfer']
            self.stdout.write(
                f'  删除 {inst.内部编号}；{transfer.单据编号} 行{line.行号} '
                f'数量 {line.数量} → {plan["remaining_quantity"]}'
            )
            if plan['remaining_quantity'] == 0:
                if plan['document_will_delete']:
                    self.stdout.write(
                        f'    空采购单整单删除，清理 {plan["notification_count"]} 条通知、'
                        f'{plan["approval_cc_count"]} 条审批抄送'
                    )
                else:
                    self.stdout.write('    空明细行删除，采购单其他明细保留')
            elif plan['amount_after'] != line.金额:
                self.stdout.write(f'    金额 {line.金额} → {plan["amount_after"]}')
            self.stdout.write(f'    台账在库 {plan["stock_before"]} → {plan["stock_before"] - 1}')
            self.stdout.write(
                f'    编号序列 last_no 保持 {plan["sequence_last_no"]}；'
                f'删除后下一件采购将使用 {plan["next_internal_code"]}（如未被其他操作先占用）'
            )
            if plan['reconciliation_history']:
                self.stdout.write(
                    f'    保留 {len(plan["reconciliation_history"])} 条对账历史快照及待处理问题'
                )
        self.stdout.write('  审计日志保留。')

    def _apply_plans(self, plans):
        stock_deltas = {}
        for plan in plans:
            inst = plan['instance']
            line = plan['line']
            transfer = plan['transfer']
            key = (inst.branch_id, inst.item_id)
            stock_deltas[key] = stock_deltas.get(key, 0) + 1

            for comparison in plan['reconciliation_history']:
                if not comparison.internal_code:
                    comparison.internal_code = inst.内部编号
                    comparison.save(update_fields=['internal_code'])

            TransferLineInstance.objects.filter(instance=inst).delete()
            inst.delete()
            if plan['document_will_delete']:
                Notification.objects.filter(
                    related_object_type='transfer', related_object_id=str(transfer.id),
                ).delete()
                transfer.delete()
            elif plan['remaining_quantity'] == 0:
                line.delete()
            else:
                line.数量 = plan['remaining_quantity']
                line.金额 = plan['amount_after']
                line.save(update_fields=['数量', '金额', 'updated_at'])

        for (branch_id, item_id), delta in stock_deltas.items():
            stock = AssetStock.objects.select_for_update().get(branch_id=branch_id, item_id=item_id)
            if stock.在库数量 < delta:
                raise CommandError(f'{stock.item.asset_code} 台账在库不足，已回滚')
            stock.在库数量 -= delta
            stock.save(update_fields=['在库数量', 'updated_at'])

        self.stdout.write(self.style.SUCCESS(
            f'已删除 {len(plans)} 条实例；对应采购数量与在库台账同步减少。'
        ))

    def _recheck_consistency(self):
        self.stdout.write('=== 台账对账复验 ===')
        output = StringIO()
        try:
            call_command('check_ledger_consistency', stdout=output)
        except SystemExit as exc:
            self.stdout.write(output.getvalue())
            raise CommandError('台账复验失败，事务已回滚') from exc
        self.stdout.write(self.style.SUCCESS(output.getvalue().strip()))
