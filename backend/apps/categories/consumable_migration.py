from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path

from django.db import transaction
from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.db.models import Prefetch
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.assets.services import ledger
from apps.categories.models import Category, ConsumableMigrationRun
from apps.inventories.models import branch_inventory_locked, lock_branch_inventory_rows
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine


EXPECTED_CODE_COUNT = 99
RUN_REASON_PREFIX = '消耗品迁移'
SHEET_HEADERS = {
    'overview': ['项目', '值'],
    'impact': [
        '资产编号', '品目名称', '资产类目', '物品分类', '计量单位', '当前管理方式', '迁移后管理方式',
        '分公司', '在库迁移前', '在用迁移前', '回收库迁移前', '在用清零调整量', '回收库清零调整量',
        '在库迁移后', '在用迁移后', '回收库迁移后', '迁移状态/阻断原因',
        '分公司确认数量', '分公司确认结论', '分公司说明',
    ],
    'pending': [
        '单据编号', '单据日期', '单据状态', '动作类型', '回收去向', '调出分公司', '调入分公司',
        '资产编号', '品目名称', '数量', '待审批数量尚未生效', '迁移后批准影响提示', '人工核对结果', '人工说明',
    ],
}


class MigrationInputError(Exception):
    pass


class MigrationBlocked(Exception):
    def __init__(self, snapshot):
        self.snapshot = snapshot


def read_code_file(path):
    """Read the asset-code column from the supplied workbook."""
    issues = []
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise MigrationInputError(f'无法读取 Excel 文件：{exc}') from exc

    try:
        sheet = workbook.active
        header = str(sheet.cell(1, 1).value or '').strip()
        if header != '资产编号':
            issues.append(f'首列标题应为“资产编号”，实际为“{header or "空"}”')

        codes = []
        saw_nonempty_after_blank = False
        blank_rows = []
        for row_number in range(2, sheet.max_row + 1):
            values = [cell.value for cell in sheet[row_number]]
            if not any(value is not None and str(value).strip() for value in values):
                blank_rows.append(row_number)
                continue
            if blank_rows:
                saw_nonempty_after_blank = True
            value = sheet.cell(row_number, 1).value
            if value is None or not str(value).strip():
                issues.append(f'第 {row_number} 行首列缺少资产编号')
                continue
            code = str(value).strip()
            if code != str(value):
                issues.append(f'第 {row_number} 行资产编号含首尾空格：{code}')
            codes.append(code)
        if saw_nonempty_after_blank:
            issues.append('编号清单存在中间空行')
        if len(codes) != EXPECTED_CODE_COUNT:
            issues.append(f'编号数量应为 {EXPECTED_CODE_COUNT}，实际为 {len(codes)}')
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            issues.append('重复资产编号：' + ', '.join(duplicates))
        return codes, issues
    finally:
        workbook.close()


def _action_label(value):
    return dict(Transfer.ACTION_CHOICES).get(value, value or '')


def _recovery_label(value):
    return dict(Transfer.RECOVERY_DESTINATION_CHOICES).get(value, value or '')


def _pending_rows(item_ids, lock_rows=False):
    if not item_ids:
        return []
    pending_ids = TransferLine.objects.filter(
        item_id__in=item_ids,
        transfer__审批状态='待审批',
    ).values_list('transfer_id', flat=True).distinct()
    pending_transfers = Transfer.objects.filter(
        pk__in=pending_ids, 审批状态='待审批',
    ).order_by('调拨日期', '单据编号', 'id')
    if lock_rows:
        # Approval and migration both lock pending documents before item rows.
        pending_transfers = pending_transfers.select_for_update(of=('self',))
    pending_transfers = (
        pending_transfers
        .select_related('from_branch', 'to_branch')
        .prefetch_related(
            Prefetch(
                'lines',
                queryset=TransferLine.objects.filter(item_id__in=item_ids)
                .select_related('item').order_by('行号'),
                to_attr='migration_lines',
            ),
        )
        .order_by('调拨日期', '单据编号', 'id')
    )
    rows = []
    for transfer in pending_transfers:
        for line in transfer.migration_lines:
            rows.append({
                'transfer_id': str(transfer.pk),
                'line_id': str(line.pk),
                'item_id': str(line.item_id),
                'document_number': transfer.单据编号 or str(transfer.pk),
                'date': transfer.调拨日期.isoformat() if transfer.调拨日期 else '',
                'status': transfer.审批状态,
                'action_type': transfer.action_type,
                'action_label': _action_label(transfer.action_type),
                'recovery_destination': transfer.回收去向,
                'recovery_label': _recovery_label(transfer.回收去向),
                'from_branch_id': str(transfer.from_branch_id or ''),
                'from_branch': transfer.from_branch.name if transfer.from_branch_id else '',
                'to_branch_id': str(transfer.to_branch_id or ''),
                'to_branch': transfer.to_branch.name if transfer.to_branch_id else '',
                'asset_code': line.item.asset_code,
                'asset_name': line.item.asset_name,
                'quantity': int(line.数量 or 0),
                'future_effect': (
                    '批准时按当时管理方式计算台账；消耗品领用扣在库、不进在用'
                    if transfer.action_type == Transfer.ACTION_ASSIGN
                    else '迁移后在用量为零，归还单可能因在用量不足不能通过台账校验'
                    if transfer.action_type == Transfer.ACTION_RETURN
                    else '迁移后在用量为零，回收入库可能因在用量不足不能通过台账校验；直接处置按新类型核对在库'
                    if transfer.action_type == Transfer.ACTION_RECOVERY
                    else '批准时按当时管理方式和回收去向计算台账；请人工核对'
                ),
            })
    return rows


def _impact_state(rows):
    fields = (
        'asset_code', 'branch_id', 'asset_name', 'asset_category', 'item_category',
        'unit', 'management_before', 'onhand_before', 'in_use_before', 'recycle_before', 'issues',
    )
    ordered = sorted(rows, key=lambda row: (str(row.get('asset_code', '')), str(row.get('branch_id', ''))))
    return tuple(tuple(row.get(field) for field in fields) for row in ordered)


def _pending_state(rows):
    return tuple(
        tuple(sorted(row.items()))
        for row in sorted(rows, key=lambda value: (value['transfer_id'], value['line_id']))
    )


def build_snapshot(
    codes, input_issues=None, lock_rows=False, locked_branch_ids=None,
    run_id=None, mode='DRY_RUN', expected_snapshot=None,
):
    input_issues = input_issues or []
    code_set = set(codes)
    items = list(Category.objects.filter(asset_code__in=code_set).order_by('asset_code'))
    item_ids = [item.pk for item in items]

    # Approval and migration both lock pending documents before categories.
    pending_rows = _pending_rows(item_ids, lock_rows=lock_rows)
    stocks_qs = AssetStock.objects.filter(item_id__in=item_ids).select_related('branch', 'item')
    stocks = list(stocks_qs.order_by('branch_id', 'item_id'))
    locked_pending_keys = {
        (row['transfer_id'], row['line_id']) for row in pending_rows
    }
    locked_stock_ids = {str(stock.pk) for stock in stocks}

    blockers = list(input_issues)
    if lock_rows:
        locked_categories = Category.objects.filter(asset_code__in=code_set).order_by('asset_code')
        if connections[DEFAULT_DB_ALIAS].features.has_select_for_no_key_update:
            locked_categories = locked_categories.select_for_update(no_key=True)
        else:
            locked_categories = locked_categories.select_for_update()
        locked_items = list(locked_categories)
        if {item.pk for item in locked_items} != set(item_ids):
            blockers.append('加锁期间目标品目范围发生变化，请重新预演')
        items = locked_items
        item_ids = [item.pk for item in items]

        # Re-read without acquiring new Transfer locks: approvals take Branch ->
        # Transfer -> Category, so locking a newly-created document here would
        # invert that order while this transaction already holds Category.
        current_pending_rows = _pending_rows(item_ids, lock_rows=False)
        current_pending_keys = {
            (row['transfer_id'], row['line_id']) for row in current_pending_rows
        }
        if current_pending_keys != locked_pending_keys:
            blockers.append('加锁期间待审批单据范围发生变化，请重新预演')
        pending_rows = current_pending_rows

        current_stocks = list(
            AssetStock.objects.filter(item_id__in=item_ids)
            .select_related('branch', 'item').select_for_update(of=('self',))
            .order_by('branch_id', 'item_id')
        )
        if {str(stock.pk) for stock in current_stocks} != locked_stock_ids:
            blockers.append('加锁期间台账行范围发生变化，请重新预演')
        stocks = current_stocks

    item_by_code = {item.asset_code: item for item in items}
    stocks_by_item = defaultdict(list)
    relevant_branch_ids = set()
    for stock in stocks:
        stocks_by_item[stock.item.asset_code].append(stock)
        relevant_branch_ids.add(str(stock.branch_id))

    fixed_asset_item_ids = set(FixedAsset.objects.filter(item_id__in=item_ids).values_list('item_id', flat=True))
    for row in pending_rows:
        if row['from_branch_id']:
            relevant_branch_ids.add(row['from_branch_id'])
        if row['to_branch_id']:
            relevant_branch_ids.add(row['to_branch_id'])

    branches = {
        str(branch.pk): branch
        for branch in Branch.objects.filter(pk__in=relevant_branch_ids).order_by('id')
    }
    unlocked_branch_ids = relevant_branch_ids - set(locked_branch_ids or ())
    if lock_rows and unlocked_branch_ids:
        blockers.append(
            '加锁期间关联分公司范围发生变化，请重新预演：'
            + '、'.join(sorted(unlocked_branch_ids))
        )
    active_branch_inventory_ids = {
        branch_id for branch_id, branch in branches.items()
        if branch_inventory_locked(branch)
    }
    if len(codes) != EXPECTED_CODE_COUNT:
        message = f'清单应包含 {EXPECTED_CODE_COUNT} 个编号，实际为 {len(codes)}'
        if message not in blockers:
            blockers.append(message)
    if len(code_set) != len(codes):
        blockers.append('清单存在重复编号')
    missing = sorted(code_set - set(item_by_code))
    for code in missing:
        blockers.append(f'{code}：生产品目字典中不存在')

    item_issues = defaultdict(list)
    for item in items:
        if item.management_type != Category.MANAGEMENT_QUANTITY:
            item_issues[item.asset_code].append(f'当前管理方式不是数量管理（{item.management_type}）')
        if item.pk in fixed_asset_item_ids:
            item_issues[item.asset_code].append('存在固定资产实例档案')
        for stock in stocks_by_item[item.asset_code]:
            if str(stock.branch_id) in active_branch_inventory_ids:
                item_issues[item.asset_code].append(f'{stock.branch.name}正在盘点')

    for pending in pending_rows:
        for branch_key in (pending['from_branch_id'], pending['to_branch_id']):
            if branch_key and branch_key in active_branch_inventory_ids:
                item_issues[pending['asset_code']].append(
                    f'{branches[branch_key].name}正在盘点（有关联待审批单）'
                )

    for code, reasons in item_issues.items():
        for reason in dict.fromkeys(reasons):
            blockers.append(f'{code}：{reason}')

    batch_ok = not blockers
    impact_rows = []
    for code in codes:
        item = item_by_code.get(code)
        rows = stocks_by_item.get(code, [])
        if not item:
            impact_rows.append({
                'asset_code': code, 'issues': '生产品目字典中不存在', 'migration_status': '阻断',
            })
            continue
        if not rows:
            rows = [None]
        for stock in rows:
            branch_id = str(stock.branch_id) if stock else ''
            branch = stock.branch if stock else None
            row_reasons = list(dict.fromkeys(item_issues.get(code, [])))
            if stock and branch_id in active_branch_inventory_ids and not any(branch.name in reason for reason in row_reasons):
                row_reasons.append(f'{branch.name}正在盘点')
            onhand = int(stock.在库数量 or 0) if stock else 0
            in_use = int(stock.在用数量 or 0) if stock else 0
            recycle = int(stock.回收库数量 or 0) if stock else 0
            can_clear_balances = item.management_type == Category.MANAGEMENT_QUANTITY and not row_reasons
            planned_in_use_delta = -in_use if can_clear_balances else 0
            planned_recycle_delta = -recycle if can_clear_balances else 0
            migrates = batch_ok and item.management_type == Category.MANAGEMENT_QUANTITY
            impact_rows.append({
                'asset_code': code,
                'asset_name': item.asset_name,
                'asset_category': item.asset_category,
                'item_category': item.item_category,
                'unit': item.unit,
                'management_before': item.management_type,
                'management_after': Category.MANAGEMENT_CONSUMABLE if migrates else item.management_type,
                'branch_id': branch_id,
                'branch': branch.name if branch else '',
                'onhand_before': onhand,
                'in_use_before': in_use,
                'recycle_before': recycle,
                'in_use_delta': planned_in_use_delta if migrates or mode == 'DRY_RUN' else 0,
                'recycle_delta': planned_recycle_delta if migrates or mode == 'DRY_RUN' else 0,
                'onhand_after': onhand if migrates else None,
                'in_use_after': 0 if migrates else None,
                'recycle_after': 0 if migrates else None,
                'issues': '；'.join(row_reasons),
                'migration_status': '可迁移' if migrates else ('阻断' if blockers else '未执行'),
            })

    if expected_snapshot is not None and (
        _impact_state(impact_rows) != _impact_state(expected_snapshot['impact_rows'])
        or _pending_state(pending_rows) != _pending_state(expected_snapshot['pending_rows'])
    ):
        blockers.append('事务预检期间影响范围或余额发生变化，请重新预演并重新审阅')

    input_branch_ids = {row[k] for row in pending_rows for k in ('from_branch_id', 'to_branch_id') if row[k]}
    all_branch_ids = relevant_branch_ids | {value for value in input_branch_ids}
    now = timezone.localtime(timezone.now()).isoformat(timespec='seconds')
    return {
        'format_version': 1,
        'run_id': str(run_id or uuid.uuid4()),
        'mode': mode,
        'status': '阻断' if blockers else ('已执行待导出' if mode == 'APPLIED' else '可执行预演'),
        'generated_at': now,
        'source_filename': '',
        'source_sha256': '',
        'target_count': len(codes),
        'matched_count': len(item_by_code),
        'branch_count': len(all_branch_ids),
        'branch_ids': sorted(all_branch_ids),
        'blockers': list(dict.fromkeys(blockers)),
        'impact_rows': impact_rows,
        'pending_rows': pending_rows,
    }


def _actualize_snapshot(snapshot):
    impact_rows = snapshot['impact_rows']
    codes = {row['asset_code'] for row in impact_rows if row.get('branch_id') or row.get('asset_code')}
    items = {item.asset_code: item for item in Category.objects.filter(asset_code__in=codes)}
    stock_rows = AssetStock.objects.filter(item__asset_code__in=codes).select_related('branch', 'item')
    stock_by_key = {(row.item.asset_code, str(row.branch_id)): row for row in stock_rows}
    for row in impact_rows:
        item = items.get(row['asset_code'])
        if not item:
            raise RuntimeError(f"迁移后找不到品目：{row['asset_code']}")
        if item.management_type != Category.MANAGEMENT_CONSUMABLE:
            raise RuntimeError(f"迁移后管理方式不符：{row['asset_code']}={item.management_type}")
        row['management_after'] = item.management_type
        stock = stock_by_key.get((row['asset_code'], row.get('branch_id', '')))
        if stock:
            row.update({
                'onhand_after': int(stock.在库数量 or 0),
                'in_use_after': int(stock.在用数量 or 0),
                'recycle_after': int(stock.回收库数量 or 0),
            })
        else:
            row.update({'onhand_after': 0, 'in_use_after': 0, 'recycle_after': 0})
        if row['onhand_after'] != row['onhand_before']:
            raise RuntimeError(
                f"迁移不应改变在库量：{row['asset_code']} / {row.get('branch', '')} "
                f"{row['onhand_before']} -> {row['onhand_after']}"
            )
        if row['in_use_after'] != 0 or row['recycle_after'] != 0:
            raise RuntimeError(
                f"迁移后非在库余额未清零：{row['asset_code']} / {row.get('branch', '')} "
                f"在用={row['in_use_after']} 回收库={row['recycle_after']}"
            )
        row['migration_status'] = '已迁移'
    snapshot['status'] = '已执行待导出'
    return snapshot


def apply_migration(codes, input_issues, source_path, source_sha256):
    run_id = uuid.uuid4()
    try:
        discovered = build_snapshot(
            codes, input_issues=input_issues, mode='APPLIED',
        )
        if discovered['blockers']:
            raise MigrationBlocked(discovered)
        with transaction.atomic():
            branch_ids = set(discovered['branch_ids'])
            locked_branches = {
                str(branch.pk) for branch in lock_branch_inventory_rows(branch_ids)
            }
            snapshot = build_snapshot(
                codes, input_issues=input_issues, lock_rows=True,
                locked_branch_ids=locked_branches,
                run_id=run_id, mode='APPLIED', expected_snapshot=discovered,
            )
            if snapshot['blockers']:
                raise MigrationBlocked(snapshot)

            run = ConsumableMigrationRun.objects.create(
                id=run_id,
                source_filename=Path(source_path).name,
                source_sha256=source_sha256,
                asset_codes=list(codes),
                snapshot={},
                status=ConsumableMigrationRun.STATUS_APPLIED,
            )

            item_by_code = {
                item.asset_code: item
                for item in Category.objects.filter(asset_code__in=codes).order_by('asset_code')
            }
            branch_by_id = {str(branch.pk): branch for branch in Branch.objects.all()}
            for row in sorted(
                snapshot['impact_rows'],
                key=lambda value: (value.get('branch_id', ''), value['asset_code']),
            ):
                if not row.get('branch_id'):
                    continue
                for target_column, before_value, label in (
                    (LedgerAdjustment.TARGET_IN_USE, row['in_use_before'], '在用'),
                    (LedgerAdjustment.TARGET_RECYCLE, row['recycle_before'], '回收库'),
                ):
                    if not before_value:
                        continue
                    ledger.apply_adjustment(
                        branch_by_id[row['branch_id']],
                        item_by_code[row['asset_code']],
                        target_column,
                        -int(before_value),
                        f'{RUN_REASON_PREFIX} {run_id}：清零{label}余额',
                        check_inventory_lock=True,
                    )

            updated = Category.objects.filter(
                asset_code__in=codes,
                management_type=Category.MANAGEMENT_QUANTITY,
            ).update(management_type=Category.MANAGEMENT_CONSUMABLE)
            if updated != EXPECTED_CODE_COUNT:
                raise RuntimeError(f'品目管理方式更新数量异常：预期 {EXPECTED_CODE_COUNT}，实际 {updated}')

            snapshot = _actualize_snapshot(snapshot)
            snapshot.update({
                'source_filename': Path(source_path).name,
                'source_sha256': source_sha256,
                'applied_at': timezone.localtime(timezone.now()).isoformat(timespec='seconds'),
            })
            run.snapshot = snapshot
            run.save(update_fields=['snapshot', 'updated_at'])
        return run
    except MigrationBlocked:
        raise
    except Exception as exc:
        raise RuntimeError(f'迁移事务失败，数据库变更已回滚：{exc}') from exc


def _write_text(cell, value):
    cell.value = value
    if isinstance(value, str):
        cell.data_type = 's'


def _append_values(sheet, values):
    row_number = 1 if sheet.max_row == 1 and sheet.cell(1, 1).value is None else sheet.max_row + 1
    for column_number, value in enumerate(values, 1):
        _write_text(sheet.cell(row=row_number, column=column_number), value)


def _style_sheet(sheet, widths):
    fill = PatternFill('solid', fgColor='1F4E78')
    font = Font(color='FFFFFF', bold=True)
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    sheet.row_dimensions[1].height = 32
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.showGridLines = False
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical='top', wrap_text=True)


def make_workbook(snapshot):
    workbook = Workbook()
    overview = workbook.active
    overview.title = '总览'
    impact = workbook.create_sheet('迁移影响')
    pending = workbook.create_sheet('待审批明细')

    summary = [
        ('运行标识', snapshot['run_id']),
        ('运行模式', '预演（未写入）' if snapshot['mode'] == 'DRY_RUN' else '已执行'),
        ('运行状态', snapshot['status']),
        ('生成时间', snapshot.get('applied_at') or snapshot['generated_at']),
        ('输入文件', snapshot.get('source_filename') or ''),
        ('输入文件 SHA-256', snapshot.get('source_sha256') or ''),
        ('目标编号数', snapshot['target_count']),
        ('匹配品目数', snapshot['matched_count']),
        ('涉及分公司数', snapshot['branch_count']),
        ('影响明细行数', len(snapshot['impact_rows'])),
        ('待审批明细行数', len(snapshot['pending_rows'])),
        ('待审批单据数', len({row['document_number'] for row in snapshot['pending_rows']})),
        ('待审批数量口径', '仅展示单行数量；不同品目单位可能不同，不汇总为统一总量'),
        ('待审批说明', '待审批明细尚未生效；本命令不审批、不驳回、不撤回、不修改单据'),
        ('迁移库存口径', '保留在库量；在用量与回收库量通过正式台账调整清零'),
        ('预检阻断数', len(snapshot['blockers'])),
        ('预检阻断说明', '；'.join(snapshot['blockers'])),
    ]
    _append_values(overview, SHEET_HEADERS['overview'])
    for row in summary:
        _append_values(overview, row)
    _style_sheet(overview, [30, 110])

    _append_values(impact, SHEET_HEADERS['impact'])
    for row in snapshot['impact_rows']:
        _append_values(impact, [
            row.get('asset_code', ''), row.get('asset_name', ''), row.get('asset_category', ''),
            row.get('item_category', ''), row.get('unit', ''), row.get('management_before', ''),
            row.get('management_after', ''), row.get('branch', ''), row.get('onhand_before', ''),
            row.get('in_use_before', ''), row.get('recycle_before', ''),
            row.get('in_use_delta', ''), row.get('recycle_delta', ''),
            row.get('onhand_after', ''), row.get('in_use_after', ''), row.get('recycle_after', ''),
            row.get('issues') or row.get('migration_status', ''), '', '', '',
        ])
    _style_sheet(impact, [15, 20, 20, 18, 12, 16, 18, 22, 14, 14, 14, 16, 16, 14, 14, 14, 44, 18, 18, 32])

    _append_values(pending, SHEET_HEADERS['pending'])
    for row in snapshot['pending_rows']:
        _append_values(pending, [
            row['document_number'], row['date'], row['status'], row['action_label'], row['recovery_label'],
            row['from_branch'], row['to_branch'], row['asset_code'], row['asset_name'], row['quantity'],
            '否', row['future_effect'], '', '',
        ])
    _style_sheet(pending, [22, 14, 14, 14, 18, 22, 22, 15, 20, 12, 22, 60, 20, 32])
    return workbook


def write_workbook(snapshot, output_path, force=False):
    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not force:
        raise FileExistsError(f'输出文件已存在；确认覆盖时请使用 --force：{output_path}')
    file_descriptor, temporary_path = tempfile.mkstemp(
        prefix=f'.{output_path.stem}-', suffix='.xlsx', dir=output_path.parent,
    )
    os.close(file_descriptor)
    try:
        make_workbook(snapshot).save(temporary_path)
        os.replace(temporary_path, output_path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise
    return output_path
