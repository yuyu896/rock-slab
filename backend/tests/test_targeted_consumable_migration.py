import hashlib
from datetime import date
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import Workbook, load_workbook

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.assets.services import ledger
from apps.categories.models import Category, ConsumableMigrationRun
from apps.inventories.models import InventoryTask
from apps.transfers.models import Transfer, TransferLine


COUNT = 99


def _make_items():
    items = []
    for index in range(COUNT):
        code = f'TCM-{index:03d}'
        items.append(Category.objects.create(
            asset_category='测试类目',
            item_category='测试分类',
            asset_name=f'迁移测试品目 {index}',
            asset_code=code,
            unit='个',
            management_type=Category.MANAGEMENT_QUANTITY,
        ))
    return items


def _xlsx(path, codes):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Sheet1'
    sheet.append(['资产编号'])
    for code in codes:
        sheet.append([code])
    workbook.save(path)
    return path


def _run(input_path, output_path, *extra):
    extra = list(extra)
    if '--apply' in extra and '--expected-sha256' not in extra:
        extra.extend([
            '--expected-sha256',
            hashlib.sha256(input_path.read_bytes()).hexdigest(),
        ])
    return call_command(
        'migrate_consumable_list',
        '--input', str(input_path),
        '--output', str(output_path),
        *extra,
    )


def _pending_assign(branch, item):
    transfer = Transfer.objects.create(
        action_type=Transfer.ACTION_ASSIGN,
        调拨日期=date(2026, 10, 1),
        调出分公司=branch.name,
        from_branch=branch,
        审批状态='待审批',
        单据编号=f'PENDING-{item.asset_code}',
    )
    line = TransferLine.objects.create(
        transfer=transfer, item=item, 行号=1, 数量=2, 使用人='仅用于测试',
    )
    return transfer, line


@pytest.mark.django_db
def test_dry_run_is_read_only_and_writes_complete_branch_workbook(tmp_path, branch, second_branch):
    items = _make_items()
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_STOCK, 10, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 3, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_RECYCLE, 2, '测试初始化')
    ledger.apply_adjustment(second_branch, target, ledger.COLUMN_STOCK, 4, '测试初始化')
    ledger.apply_adjustment(second_branch, target, ledger.COLUMN_IN_USE, 2, '测试初始化')
    ledger.apply_adjustment(second_branch, target, ledger.COLUMN_RECYCLE, 1, '测试初始化')
    _pending_assign(branch, target)
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'preview.xlsx'
    before_adjustments = LedgerAdjustment.objects.count()

    _run(source, output)

    target.refresh_from_db()
    assert target.management_type == Category.MANAGEMENT_QUANTITY
    assert LedgerAdjustment.objects.count() == before_adjustments
    assert ConsumableMigrationRun.objects.count() == 0
    stock = AssetStock.objects.get(branch=branch, item=target)
    assert (stock.在库数量, stock.在用数量, stock.回收库数量) == (10, 3, 2)

    workbook = load_workbook(output, read_only=True, data_only=True)
    assert workbook.sheetnames == ['总览', '迁移影响', '待审批明细']
    impact = list(workbook['迁移影响'].iter_rows(values_only=True))
    assert len(impact) == 1 + COUNT + 1  # 其余 98 个编号各列一条零余额占位行
    target_rows = [row for row in impact[1:] if row[0] == target.asset_code]
    assert {(row[7], row[9], row[10], row[11], row[12], row[13], row[14], row[15]) for row in target_rows} == {
        (branch.name, 3, 2, -3, -2, 10, 0, 0),
        (second_branch.name, 2, 1, -2, -1, 4, 0, 0),
    }
    pending = list(workbook['待审批明细'].iter_rows(values_only=True))
    assert len(pending) == 2
    assert pending[1][0] == f'PENDING-{target.asset_code}'
    assert pending[1][2] == '待审批'
    assert pending[1][9] == 2
    assert pending[1][10] == '否'
    assert '消耗品领用扣在库' in pending[1][11]
    assert '使用人' not in pending[0]
    workbook.close()


@pytest.mark.django_db
def test_apply_clears_in_use_by_branch_and_preserves_pending_document(tmp_path, branch, second_branch):
    items = _make_items()
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_STOCK, 12, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 3, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_RECYCLE, 2, '测试初始化')
    ledger.apply_adjustment(second_branch, target, ledger.COLUMN_STOCK, 6, '测试初始化')
    ledger.apply_adjustment(second_branch, target, ledger.COLUMN_IN_USE, 2, '测试初始化')
    ledger.apply_adjustment(second_branch, target, ledger.COLUMN_RECYCLE, 1, '测试初始化')
    transfer, line = _pending_assign(branch, target)
    historical = Transfer.objects.create(
        action_type=Transfer.ACTION_ASSIGN,
        调拨日期=date(2026, 9, 1),
        调出分公司=branch.name,
        from_branch=branch,
        审批状态='已通过',
        单据编号=f'HISTORY-{target.asset_code}',
    )
    historical_line = TransferLine.objects.create(
        transfer=historical, item=target, 行号=1, 数量=4, 使用人='历史记录',
    )
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'result.xlsx'
    adjustment_count_before = LedgerAdjustment.objects.count()

    _run(source, output, '--apply')

    target.refresh_from_db()
    transfer.refresh_from_db()
    line.refresh_from_db()
    historical.refresh_from_db()
    historical_line.refresh_from_db()
    assert target.management_type == Category.MANAGEMENT_CONSUMABLE
    assert transfer.审批状态 == '待审批'
    assert line.数量 == 2
    assert historical.审批状态 == '已通过'
    assert historical_line.数量 == 4
    assert LedgerAdjustment.objects.count() == adjustment_count_before + 4
    assert LedgerAdjustment.objects.filter(
        item=target, 目标列=LedgerAdjustment.TARGET_IN_USE,
        事由__contains='消耗品迁移',
    ).count() == 2
    assert LedgerAdjustment.objects.filter(
        item=target, 目标列=LedgerAdjustment.TARGET_RECYCLE,
        事由__contains='消耗品迁移',
    ).count() == 2
    first = AssetStock.objects.get(branch=branch, item=target)
    second = AssetStock.objects.get(branch=second_branch, item=target)
    assert (first.在库数量, first.在用数量, first.回收库数量) == (12, 0, 0)
    assert (second.在库数量, second.在用数量, second.回收库数量) == (6, 0, 0)
    run = ConsumableMigrationRun.objects.get()
    assert run.status == ConsumableMigrationRun.STATUS_REPORTED
    assert run.report_path == str(output.resolve())

    workbook = load_workbook(output, read_only=True, data_only=True)
    impact = list(workbook['迁移影响'].iter_rows(values_only=True))
    target_rows = [row for row in impact[1:] if row[0] == target.asset_code]
    assert {(row[7], row[9], row[10], row[11], row[12], row[13], row[14], row[15]) for row in target_rows} == {
        (branch.name, 3, 2, -3, -2, 12, 0, 0),
        (second_branch.name, 2, 1, -2, -1, 6, 0, 0),
    }
    workbook.close()


@pytest.mark.django_db
def test_nonzero_recycle_balance_is_cleared_and_onhand_is_preserved(tmp_path, branch):
    items = _make_items()
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_STOCK, 5, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 3, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_RECYCLE, 1, '测试初始化')
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'cleared.xlsx'
    before_adjustments = LedgerAdjustment.objects.count()

    _run(source, output, '--apply')

    assert output.exists()
    target.refresh_from_db()
    assert target.management_type == Category.MANAGEMENT_CONSUMABLE
    assert LedgerAdjustment.objects.count() == before_adjustments + 2
    stock = AssetStock.objects.get(branch=branch, item=target)
    assert (stock.在库数量, stock.在用数量, stock.回收库数量) == (5, 0, 0)
    assert LedgerAdjustment.objects.filter(
        item=target, 目标列=LedgerAdjustment.TARGET_IN_USE,
        事由__contains='消耗品迁移',
    ).exists()
    assert LedgerAdjustment.objects.filter(
        item=target, 目标列=LedgerAdjustment.TARGET_RECYCLE,
        事由__contains='消耗品迁移',
    ).exists()
    workbook = load_workbook(output, read_only=True, data_only=True)
    impact = list(workbook['迁移影响'].iter_rows(values_only=True))
    target_row = next(row for row in impact[1:] if row[0] == target.asset_code)
    assert (target_row[8], target_row[9], target_row[10], target_row[11], target_row[12]) == (
        5, 3, 1, -3, -1,
    )
    assert (target_row[13], target_row[14], target_row[15]) == (5, 0, 0)
    workbook.close()


@pytest.mark.django_db
def test_invalid_duplicate_list_cannot_partially_migrate(tmp_path):
    items = _make_items()
    codes = [item.asset_code for item in items]
    codes[1] = codes[0]
    source = _xlsx(tmp_path / 'duplicate.xlsx', codes)
    output = tmp_path / 'invalid.xlsx'

    with pytest.raises(CommandError, match='清单存在重复编号'):
        _run(source, output, '--apply')

    assert Category.objects.filter(management_type=Category.MANAGEMENT_CONSUMABLE).count() == 0
    assert ConsumableMigrationRun.objects.count() == 0
    assert output.exists()


@pytest.mark.django_db
def test_apply_requires_the_reviewed_input_hash(tmp_path):
    items = _make_items()
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'result.xlsx'

    with pytest.raises(CommandError, match='必须提供已审阅预演工作簿'):
        call_command(
            'migrate_consumable_list', '--input', str(source),
            '--output', str(output), '--apply',
        )

    assert Category.objects.get(pk=items[0].pk).management_type == Category.MANAGEMENT_QUANTITY
    assert ConsumableMigrationRun.objects.count() == 0


@pytest.mark.django_db
def test_apply_rejects_a_changed_input_hash_before_writing(tmp_path):
    items = _make_items()
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'result.xlsx'

    with pytest.raises(CommandError, match='与已审阅预演不一致'):
        _run(source, output, '--apply', '--expected-sha256', '0' * 64)

    assert Category.objects.get(pk=items[0].pk).management_type == Category.MANAGEMENT_QUANTITY
    assert ConsumableMigrationRun.objects.count() == 0


@pytest.mark.django_db
def test_unknown_code_blocks_all_migrations(tmp_path):
    items = _make_items()
    codes = [item.asset_code for item in items]
    codes[-1] = 'TCM-UNKNOWN'
    source = _xlsx(tmp_path / 'unknown.xlsx', codes)
    output = tmp_path / 'unknown-report.xlsx'

    with pytest.raises(CommandError, match='生产品目字典中不存在'):
        _run(source, output, '--apply')

    assert Category.objects.filter(management_type=Category.MANAGEMENT_CONSUMABLE).count() == 0
    assert ConsumableMigrationRun.objects.count() == 0
    workbook = load_workbook(output, read_only=True, data_only=True)
    impact = list(workbook['迁移影响'].iter_rows(values_only=True))
    assert any(row[0] == 'TCM-UNKNOWN' and '不存在' in str(row[16]) for row in impact[1:])
    workbook.close()


@pytest.mark.django_db
def test_management_type_drift_blocks_all_migrations(tmp_path):
    items = _make_items()
    items[0].management_type = Category.MANAGEMENT_CONSUMABLE
    items[0].save(update_fields=['management_type'])
    source = _xlsx(tmp_path / 'drift.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'drift-report.xlsx'

    with pytest.raises(CommandError, match='当前管理方式不是数量管理'):
        _run(source, output, '--apply')

    assert Category.objects.filter(management_type=Category.MANAGEMENT_CONSUMABLE).count() == 1
    assert ConsumableMigrationRun.objects.count() == 0


@pytest.mark.django_db
def test_active_branch_inventory_lock_blocks_migration(tmp_path, branch):
    items = _make_items()
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 2, '测试初始化')
    InventoryTask.objects.create(name='正在进行的盘点', branch=branch, status='in_progress')
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'locked.xlsx'

    with pytest.raises(CommandError, match='正在盘点'):
        _run(source, output, '--apply')

    target.refresh_from_db()
    stock = AssetStock.objects.get(branch=branch, item=target)
    assert target.management_type == Category.MANAGEMENT_QUANTITY
    assert stock.在用数量 == 2
    assert ConsumableMigrationRun.objects.count() == 0


@pytest.mark.django_db
def test_apply_with_explicit_inventory_lock_override_preserves_task_and_clears_balances(
    tmp_path, branch,
):
    items = _make_items()
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_STOCK, 10, '娴嬭瘯鍒濆鍖?')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 3, '娴嬭瘯鍒濆鍖?')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_RECYCLE, 2, '娴嬭瘯鍒濆鍖?')
    task = InventoryTask.objects.create(
        name='娴嬭瘯娲诲姩鐩樼偣', branch=branch, status='in_progress',
    )
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'override.xlsx'

    _run(source, output, '--apply', '--ignore-inventory-locks')

    target.refresh_from_db()
    task.refresh_from_db()
    stock = AssetStock.objects.get(branch=branch, item=target)
    assert target.management_type == Category.MANAGEMENT_CONSUMABLE
    assert (
        getattr(stock, '\u5728\u5e93\u6570\u91cf'),
        getattr(stock, '\u5728\u7528\u6570\u91cf'),
        getattr(stock, '\u56de\u6536\u5e93\u6570\u91cf'),
    ) == (10, 0, 0)
    assert task.status == 'in_progress'
    assert task.branch_id == branch.pk
    assert ConsumableMigrationRun.objects.count() == 1

    workbook = load_workbook(output, read_only=True, data_only=True)
    overview = list(workbook.worksheets[0].iter_rows(values_only=True))
    overview_values = {row[0]: row[1] for row in overview[1:] if row and row[0]}
    assert overview_values['Active inventory override'] == 'enabled'
    assert str(task.pk) in overview_values['Active inventory tasks at run']
    workbook.close()


@pytest.mark.django_db
def test_fixed_asset_records_block_migration(tmp_path, branch):
    items = _make_items()
    target = items[0]
    FixedAsset.objects.create(item=target, 内部编号='TCM-FIXED-001', branch=branch)
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'fixed.xlsx'

    with pytest.raises(CommandError, match='存在固定资产实例档案'):
        _run(source, output, '--apply')

    target.refresh_from_db()
    assert target.management_type == Category.MANAGEMENT_QUANTITY
    assert ConsumableMigrationRun.objects.count() == 0


@pytest.mark.django_db
def test_apply_rolls_back_when_recycle_adjustment_fails_after_in_use(tmp_path, branch, monkeypatch):
    items = _make_items()
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_STOCK, 5, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 2, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_RECYCLE, 1, '测试初始化')
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    output = tmp_path / 'rollback.xlsx'
    count_before = LedgerAdjustment.objects.count()
    original = ledger.apply_adjustment
    calls = 0

    def fail_second_adjustment(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('模拟第二条调整失败')
        return original(*args, **kwargs)

    monkeypatch.setattr(ledger, 'apply_adjustment', fail_second_adjustment)
    with pytest.raises(CommandError, match='数据库变更已回滚'):
        _run(source, output, '--apply')

    assert calls == 2
    assert LedgerAdjustment.objects.count() == count_before
    assert ConsumableMigrationRun.objects.count() == 0
    target.refresh_from_db()
    assert target.management_type == Category.MANAGEMENT_QUANTITY
    stock = AssetStock.objects.get(branch=branch, item=target)
    assert (stock.在库数量, stock.在用数量, stock.回收库数量) == (5, 2, 1)


@pytest.mark.django_db
def test_failed_export_can_be_rebuilt_from_run_snapshot_without_reapplying(tmp_path, branch, monkeypatch):
    items = _make_items()
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 3, '测试初始化')
    ledger.apply_adjustment(branch, target, ledger.COLUMN_RECYCLE, 2, '测试初始化')
    source = _xlsx(tmp_path / 'codes.xlsx', [item.asset_code for item in items])
    failed_output = tmp_path / 'not-written.xlsx'
    count_before = LedgerAdjustment.objects.count()

    import apps.categories.management.commands.migrate_consumable_list as command_module

    def fail_workbook(*args, **kwargs):
        raise OSError('模拟磁盘写入失败')

    monkeypatch.setattr(command_module, 'write_workbook', fail_workbook)
    with pytest.raises(CommandError, match='数据库事务已经提交') as error:
        _run(source, failed_output, '--apply')
    run_id = str(error.value).split('--run-id ', 1)[1].split()[0]
    run = ConsumableMigrationRun.objects.get(pk=run_id)
    assert run.status == ConsumableMigrationRun.STATUS_APPLIED
    target.refresh_from_db()
    assert target.management_type == Category.MANAGEMENT_CONSUMABLE
    assert LedgerAdjustment.objects.count() == count_before + 2
    stock = AssetStock.objects.get(branch=branch, item=target)
    assert (stock.在库数量, stock.在用数量, stock.回收库数量) == (0, 0, 0)

    monkeypatch.undo()
    output = tmp_path / 'reexport.xlsx'
    call_command('migrate_consumable_list', '--run-id', run_id, '--output', str(output))

    assert output.exists()
    assert LedgerAdjustment.objects.count() == count_before + 2
    run.refresh_from_db()
    assert run.status == ConsumableMigrationRun.STATUS_REPORTED
    workbook = load_workbook(output, read_only=True, data_only=True)
    impact = list(workbook['迁移影响'].iter_rows(values_only=True))
    target_row = next(row for row in impact[1:] if row[0] == target.asset_code)
    assert (target_row[9], target_row[10], target_row[11], target_row[12]) == (3, 2, -3, -2)
    assert (target_row[13], target_row[14], target_row[15]) == (0, 0, 0)
    workbook.close()
