from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
import time

import pytest
from django.db import close_old_connections, connection, transaction
from rest_framework.exceptions import ValidationError

from apps.assets.models import AssetStock
from apps.assets.services import ledger
from apps.categories.consumable_migration import (
    MigrationBlocked,
    apply_migration,
)
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer
from apps.inventories.models import (
    InventoryItem, InventoryTask, lock_branch_inventory_rows,
)
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine
from apps.transfers.services import lock_line_item_categories, validate_line_items_instances
from conftest import _client_for


def _make_quantity_item(code):
    return Category.objects.create(
        asset_category='并发迁移测试',
        item_category='办公用品',
        asset_name=f'迁移测试品目 {code}',
        asset_code=code,
        unit='个',
        management_type=Category.MANAGEMENT_QUANTITY,
    )


def _watch_migration_lock_wait(monkeypatch):
    from apps.categories import consumable_migration

    original = consumable_migration.lock_branch_inventory_rows
    attempted_lock = Event()
    backend_pid = {}

    def watched_lock_branch_rows(*args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_backend_pid()')
            backend_pid['value'] = cursor.fetchone()[0]
        attempted_lock.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(consumable_migration, 'lock_branch_inventory_rows', watched_lock_branch_rows)
    return attempted_lock, backend_pid


def _wait_for_postgres_lock_wait(backend_pid):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s',
                [backend_pid],
            )
            row = cursor.fetchone()
        if row and row[0] == 'Lock':
            return True
        time.sleep(0.01)
    return False


@pytest.mark.django_db
def test_transfer_validation_reloads_a_stale_category(branch):
    item = _make_quantity_item('TCM-STALE-001')
    stale_item = Category.objects.get(pk=item.pk)
    Category.objects.filter(pk=item.pk).update(
        management_type=Category.MANAGEMENT_CONSUMABLE,
    )
    entry = {'item': stale_item, '数量': 1, 'instances': []}

    lock_line_item_categories([entry])

    assert entry['item'].management_type == Category.MANAGEMENT_CONSUMABLE
    with pytest.raises(ValidationError, match='消耗品无回收'):
        validate_line_items_instances(
            Transfer.ACTION_RECOVERY, branch, None, Transfer.ASSIGN_SOURCE_STOCK,
            [entry], recovery_dest=Transfer.RESTOCK,
        )


@pytest.mark.django_db
def test_ledger_adjustment_rejects_a_stale_category_type(branch):
    item = _make_quantity_item('TCM-STALE-ADJUST-001')
    stale_item = Category.objects.get(pk=item.pk)
    Category.objects.filter(pk=item.pk).update(
        management_type=Category.MANAGEMENT_CONSUMABLE,
    )

    with pytest.raises(ValidationError, match='品目管理方式已变化'):
        ledger.apply_adjustment(
            branch, stale_item, ledger.COLUMN_IN_USE, 1, '并发类型漂移测试',
        )

    assert not AssetStock.objects.filter(branch=branch, item=item).exists()


@pytest.mark.django_db
def test_stale_category_patch_preserves_the_locked_management_type():
    item = _make_quantity_item('TCM-STALE-PATCH-001')
    stale_item = Category.objects.get(pk=item.pk)
    Category.objects.filter(pk=item.pk).update(
        management_type=Category.MANAGEMENT_CONSUMABLE,
    )
    serializer = CategorySerializer(
        stale_item, data={'remarks': 'updated after migration'}, partial=True,
    )
    serializer.is_valid(raise_exception=True)

    updated = serializer.save()

    assert updated.management_type == Category.MANAGEMENT_CONSUMABLE
    assert updated.remarks == 'updated after migration'


@pytest.mark.django_db
def test_start_rechecks_inventory_scope_after_acquiring_branch_barrier(
    admin_user, branch, monkeypatch,
):
    from apps.inventories.views import InventoryTaskViewSet

    task = InventoryTask.objects.create(name='迁移并发盘点', branch=branch)
    values = iter((1, 0))
    monkeypatch.setattr(InventoryTaskViewSet, '_scope_count', lambda _self, _task: next(values))

    response = _client_for(admin_user).post(f'/api/inventories/{task.pk}/start')

    assert response.status_code == 400
    task.refresh_from_db()
    assert task.status == 'pending'
    assert not InventoryItem.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_global_inventory_task_blocks_migration_for_related_branches(branch, tmp_path):
    items = [
        _make_quantity_item(f'TCM-GLOBAL-{index:03d}')
        for index in range(99)
    ]
    ledger.apply_adjustment(branch, items[0], ledger.COLUMN_STOCK, 2, '测试初始化')
    InventoryTask.objects.create(
        name='全集团盘点', branch=None, status='in_progress',
    )

    with pytest.raises(MigrationBlocked) as error:
        apply_migration(
            [item.asset_code for item in items], [],
            Path(tmp_path) / 'codes.xlsx', '0' * 64,
        )

    assert any('正在盘点' in reason for reason in error.value.snapshot['blockers'])
    assert items[0].management_type == Category.MANAGEMENT_QUANTITY


@pytest.mark.django_db
def test_create_action_rechecks_inventory_lock_inside_branch_barrier(
    admin_user, branch, department, monkeypatch,
):
    from apps.inventories.models import InventoryTask
    from apps.transfers.views import TransferViewSet

    item = _make_quantity_item('TCM-CREATE-INVENTORY-LOCK')
    task = InventoryTask.objects.create(name='并发建单盘点', branch=branch)
    original_check = TransferViewSet._check_inventory_lock

    def activate_inventory_after_precheck(view, branch_name=None, branch_id=None):
        result = original_check(view, branch_name=branch_name, branch_id=branch_id)
        if branch_id == branch.pk and task.status == 'pending':
            InventoryTask.objects.filter(pk=task.pk).update(status='in_progress')
            task.status = 'in_progress'
        return result

    monkeypatch.setattr(TransferViewSet, '_check_inventory_lock', activate_inventory_after_precheck)
    response = _client_for(admin_user).post(
        '/api/transfers/assign',
        {
            '调拨日期': '2026-10-01',
            '调出分公司': branch.name,
            'items': [{
                'item': str(item.pk), '数量': 1, '使用人': '测试',
                'department': str(department.pk),
            }],
        },
        format='json',
    )

    assert response.status_code == 400
    assert not TransferLine.objects.filter(item=item).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != 'postgresql', reason='需要 PostgreSQL 行锁验证')
def test_approval_of_new_pending_document_does_not_deadlock_with_migration(
    admin_user, branch, tmp_path, monkeypatch,
):
    from apps.categories import consumable_migration

    items = [
        _make_quantity_item(f'TCM-APPROVE-RACE-{index:03d}')
        for index in range(99)
    ]
    target = items[0]
    category_locked = Event()
    allow_document_commit = Event()
    post_category_scan = Event()
    allow_post_category_scan = Event()
    migration_lock_attempted, migration_pid = _watch_migration_lock_wait(monkeypatch)
    transfer_id = {}
    scan_count = {'value': 0}
    approval_pid = {}
    approval_waiting_for_category = Event()
    original_pending_rows = consumable_migration._pending_rows
    original_apply_document = ledger.apply_document

    def pause_post_category_scan(item_ids, lock_rows=False):
        scan_count['value'] += 1
        # apply_migration does discovery, a locked precheck, then a post-category reread.
        if scan_count['value'] == 3:
            post_category_scan.set()
            if not allow_post_category_scan.wait(timeout=10):
                raise TimeoutError('test did not release migration pending scan')
        return original_pending_rows(item_ids, lock_rows=lock_rows)

    def watch_apply_document(transfer):
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_backend_pid()')
            approval_pid['value'] = cursor.fetchone()[0]
        approval_waiting_for_category.set()
        return original_apply_document(transfer)

    monkeypatch.setattr(consumable_migration, '_pending_rows', pause_post_category_scan)
    monkeypatch.setattr(ledger, 'apply_document', watch_apply_document)

    def create_pending_document():
        close_old_connections()
        try:
            with transaction.atomic():
                entry = {'item': Category.objects.get(pk=target.pk)}
                lock_line_item_categories([entry])
                category_locked.set()
                if not allow_document_commit.wait(timeout=10):
                    raise TimeoutError('test did not release pending document writer')
                transfer = Transfer.objects.create(
                    action_type=Transfer.ACTION_ASSIGN,
                    调拨日期='2026-10-01',
                    调出分公司=branch.name,
                    from_branch_id=branch.pk,
                    审批状态='待审批',
                    单据编号='TCM-APPROVE-RACE-PENDING',
                )
                TransferLine.objects.create(
                    transfer=transfer, item=entry['item'], 行号=1,
                    数量=1, 使用人='测试',
                )
                transfer_id['value'] = str(transfer.pk)
        finally:
            close_old_connections()

    def migrate():
        close_old_connections()
        try:
            return apply_migration(
                [item.asset_code for item in items], [],
                Path(tmp_path) / 'approval-race.xlsx', '4' * 64,
            )
        finally:
            close_old_connections()

    def approve_pending_document():
        close_old_connections()
        try:
            return _client_for(admin_user).post(
                f'/api/transfers/{transfer_id["value"]}/approve',
                {'approved': True}, format='json',
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=3) as pool:
        writer = pool.submit(create_pending_document)
        assert category_locked.wait(timeout=10)
        migration = pool.submit(migrate)
        try:
            assert migration_lock_attempted.wait(timeout=10)
            assert _wait_for_postgres_lock_wait(migration_pid['value'])
        finally:
            allow_document_commit.set()
        writer.result(timeout=10)
        assert post_category_scan.wait(timeout=10)
        approval = pool.submit(approve_pending_document)
        try:
            assert approval_waiting_for_category.wait(timeout=10)
            assert _wait_for_postgres_lock_wait(approval_pid['value'])
        finally:
            allow_post_category_scan.set()
        with pytest.raises(MigrationBlocked):
            migration.result(timeout=10)
        approval_response = approval.result(timeout=10)

    assert approval_response.status_code == 400
    transfer = Transfer.objects.get(pk=transfer_id['value'])
    assert transfer.审批状态 == '待审批'
    assert Category.objects.get(pk=target.pk).management_type == Category.MANAGEMENT_QUANTITY


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != 'postgresql', reason='需要 PostgreSQL 行锁验证')
def test_migration_detects_pending_document_that_wins_category_lock(
    branch, tmp_path, monkeypatch,
):
    items = [
        _make_quantity_item(f'TCM-CONCURRENT-{index:03d}')
        for index in range(99)
    ]
    codes = [item.asset_code for item in items]
    category_locked = Event()
    allow_writer_commit = Event()
    migration_lock_attempted, migration_pid = _watch_migration_lock_wait(monkeypatch)

    def create_pending_document():
        close_old_connections()
        try:
            with transaction.atomic():
                entry = {'item': Category.objects.get(pk=items[0].pk)}
                lock_line_item_categories([entry])
                category_locked.set()
                if not allow_writer_commit.wait(timeout=10):
                    raise TimeoutError('test did not release transfer writer')
                transfer = Transfer.objects.create(
                    action_type=Transfer.ACTION_ASSIGN,
                    调拨日期='2026-10-01',
                    调出分公司=branch.name,
                    from_branch_id=branch.pk,
                    审批状态='待审批',
                    单据编号='TCM-CONCURRENT-PENDING',
                )
                TransferLine.objects.create(
                    transfer=transfer, item=entry['item'], 行号=1,
                    数量=1, 使用人='测试',
                )
        finally:
            close_old_connections()

    def migrate():
        close_old_connections()
        try:
            return apply_migration(
                codes, [], Path(tmp_path) / 'codes.xlsx', '0' * 64,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(create_pending_document)
        assert category_locked.wait(timeout=10)
        migration = pool.submit(migrate)
        try:
            assert migration_lock_attempted.wait(timeout=10)
            assert _wait_for_postgres_lock_wait(migration_pid['value'])
        finally:
            allow_writer_commit.set()
        writer.result(timeout=10)
        with pytest.raises(MigrationBlocked) as error:
            migration.result(timeout=10)

    assert any('待审批单据范围发生变化' in reason for reason in error.value.snapshot['blockers'])
    assert Category.objects.get(pk=items[0].pk).management_type == Category.MANAGEMENT_QUANTITY


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != 'postgresql', reason='需要 PostgreSQL 行锁验证')
def test_migration_blocks_when_ledger_value_changes_after_preflight(
    branch, tmp_path, monkeypatch,
):
    items = [
        _make_quantity_item(f'TCM-LEDGER-RACE-{index:03d}')
        for index in range(99)
    ]
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_IN_USE, 2, '测试初始化')
    stock = AssetStock.objects.get(branch=branch, item=target)
    stock_locked = Event()
    allow_adjustment = Event()
    migration_lock_attempted, migration_pid = _watch_migration_lock_wait(monkeypatch)

    def adjust_ledger():
        close_old_connections()
        try:
            with transaction.atomic():
                lock_branch_inventory_rows([branch.pk])
                lock_line_item_categories([{'item': Category.objects.get(pk=target.pk)}])
                AssetStock.objects.select_for_update().get(pk=stock.pk)
                stock_locked.set()
                if not allow_adjustment.wait(timeout=10):
                    raise TimeoutError('test did not release ledger writer')
                ledger.apply_adjustment(
                    Branch.objects.get(pk=branch.pk),
                    Category.objects.get(pk=target.pk),
                    ledger.COLUMN_IN_USE, 3, '并发测试增加在用量',
                )
        finally:
            close_old_connections()

    def migrate():
        close_old_connections()
        try:
            return apply_migration(
                [item.asset_code for item in items], [],
                Path(tmp_path) / 'ledger-race.xlsx', '1' * 64,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(adjust_ledger)
        assert stock_locked.wait(timeout=10)
        migration = pool.submit(migrate)
        try:
            assert migration_lock_attempted.wait(timeout=10)
            assert _wait_for_postgres_lock_wait(migration_pid['value'])
        finally:
            allow_adjustment.set()
        writer.result(timeout=10)
        with pytest.raises(MigrationBlocked) as error:
            migration.result(timeout=10)

    assert any('事务预检期间' in reason for reason in error.value.snapshot['blockers'])
    target.refresh_from_db()
    stock.refresh_from_db()
    assert target.management_type == Category.MANAGEMENT_QUANTITY
    assert stock.在用数量 == 5


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != 'postgresql', reason='需要 PostgreSQL 行锁验证')
def test_migration_blocks_when_a_missing_stock_row_appears_after_preflight(
    branch, tmp_path, monkeypatch,
):
    items = [
        _make_quantity_item(f'TCM-MISSING-ROW-{index:03d}')
        for index in range(99)
    ]
    target = items[0]
    row_creation_started = Event()
    allow_row_creation = Event()
    migration_lock_attempted, migration_pid = _watch_migration_lock_wait(monkeypatch)
    original_locked_row = ledger._locked_row

    def pause_before_row_creation(*args, **kwargs):
        if not row_creation_started.is_set():
            row_creation_started.set()
            if not allow_row_creation.wait(timeout=10):
                raise TimeoutError('test did not release missing-row adjustment')
        return original_locked_row(*args, **kwargs)

    monkeypatch.setattr(ledger, '_locked_row', pause_before_row_creation)

    def adjust_missing_row():
        close_old_connections()
        try:
            return ledger.apply_adjustment(
                Branch.objects.get(pk=branch.pk),
                Category.objects.get(pk=target.pk),
                ledger.COLUMN_IN_USE, 2, '并发测试创建台账行',
            )
        finally:
            close_old_connections()

    def migrate():
        close_old_connections()
        try:
            return apply_migration(
                [item.asset_code for item in items], [],
                Path(tmp_path) / 'missing-row.xlsx', '2' * 64,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(adjust_missing_row)
        assert row_creation_started.wait(timeout=10)
        migration = pool.submit(migrate)
        try:
            assert migration_lock_attempted.wait(timeout=10)
            assert _wait_for_postgres_lock_wait(migration_pid['value'])
        finally:
            allow_row_creation.set()
        writer.result(timeout=10)
        with pytest.raises(MigrationBlocked) as error:
            migration.result(timeout=10)

    assert any('事务预检期间' in reason for reason in error.value.snapshot['blockers'])
    target.refresh_from_db()
    stock = AssetStock.objects.get(branch=branch, item=target)
    assert target.management_type == Category.MANAGEMENT_QUANTITY
    assert (stock.在库数量, stock.在用数量, stock.回收库数量) == (0, 2, 0)


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != 'postgresql', reason='需要 PostgreSQL 行锁验证')
def test_inventory_start_waits_for_migration_branch_barrier(
    admin_user, branch, tmp_path, monkeypatch,
):
    from apps.categories import consumable_migration
    from apps.inventories.views import InventoryTaskViewSet

    items = [
        _make_quantity_item(f'TCM-INVENTORY-RACE-{index:03d}')
        for index in range(99)
    ]
    target = items[0]
    ledger.apply_adjustment(branch, target, ledger.COLUMN_STOCK, 1, '测试初始化')
    task = InventoryTask.objects.create(name='迁移锁屏障测试', branch=branch)
    migration_holds_branch = Event()
    allow_migration_commit = Event()
    start_lock_attempted = Event()
    backend_pids = {}
    original_build = consumable_migration.build_snapshot
    original_barrier = InventoryTaskViewSet._lock_branch_inventory_barrier

    def hold_after_locked_snapshot(*args, **kwargs):
        snapshot = original_build(*args, **kwargs)
        if kwargs.get('lock_rows'):
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_backend_pid()')
                backend_pids['migration'] = cursor.fetchone()[0]
            migration_holds_branch.set()
            if not allow_migration_commit.wait(timeout=10):
                raise TimeoutError('test did not release migration branch barrier')
        return snapshot

    def watch_inventory_barrier(inventory_task):
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_backend_pid()')
            backend_pids['inventory'] = cursor.fetchone()[0]
        start_lock_attempted.set()
        return original_barrier(inventory_task)

    monkeypatch.setattr(consumable_migration, 'build_snapshot', hold_after_locked_snapshot)
    monkeypatch.setattr(
        InventoryTaskViewSet,
        '_lock_branch_inventory_barrier',
        staticmethod(watch_inventory_barrier),
    )

    def migrate():
        close_old_connections()
        try:
            return apply_migration(
                [item.asset_code for item in items], [],
                Path(tmp_path) / 'inventory-race.xlsx', '3' * 64,
            )
        finally:
            close_old_connections()

    def start_inventory():
        close_old_connections()
        try:
            return _client_for(admin_user).post(f'/api/inventories/{task.pk}/start')
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        migration = pool.submit(migrate)
        assert migration_holds_branch.wait(timeout=10)
        inventory = pool.submit(start_inventory)
        try:
            assert start_lock_attempted.wait(timeout=10)
            assert _wait_for_postgres_lock_wait(backend_pids['inventory'])
        finally:
            allow_migration_commit.set()
        run = migration.result(timeout=10)
        response = inventory.result(timeout=10)

    assert response.status_code == 200
    assert Category.objects.get(pk=target.pk).management_type == Category.MANAGEMENT_CONSUMABLE
    task.refresh_from_db()
    assert task.status == 'in_progress'
    entry = InventoryItem.objects.get(task=task, stock__item=target)
    assert entry.expected_qty == 1
    assert run.snapshot['status'] == '已执行待导出'
