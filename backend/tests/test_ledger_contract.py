"""台账契约测试：五单对称矩阵、唯一写入口、调整单、盘点差异自动生成调整单、报表口径。

对应 document-ledger-sync / ledger-single-source / inventory-item-basis 能力。
"""
import pytest
from rest_framework import status

from apps.assets.models import AssetStock, LedgerAdjustment
from apps.assets.services import ledger
from apps.transfers.models import Transfer


def _ensure_item(code, warning=None):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个', 'warning_line': warning,
        },
    )
    return item


def _seed(branch, code, stock=0, in_use=0, recycle=0):
    item = _ensure_item(code)
    if stock:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '测试造数')
    if in_use:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, in_use, '测试造数')
    if recycle:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_RECYCLE, recycle, '测试造数')
    return item


def _row(branch, code):
    return AssetStock.objects.get(branch=branch, item__asset_code=code)


def _create_doc(client, action, branch, code, qty, line=None, **header_extra):
    """建单：单头 + 单条明细行（line 追加行级字段如 单价/金额）。"""
    from apps.categories.models import Category
    item_line = {'item': str(Category.objects.get(asset_code=code).id), '数量': qty}
    if action == 'assign':
        # 领用行使用人/部门必填（修订 2.2）：默认注入，专用用例经 line 显式覆盖
        from apps.organizations.models import Department
        dept, _ = Department.objects.get_or_create(branch=branch, name='测试部门')
        item_line.setdefault('使用人', '张三')
        item_line.setdefault('department', str(dept.id))
    item_line.update(line or {})
    payload = {
        '调拨日期': '2026-08-23',
        '调出分公司': branch.name,
        'items': [item_line],
    }
    payload.update(header_extra)
    resp = client.post(f'/api/transfers/{action}', payload, format='json')
    assert resp.status_code == 201, resp.data
    return resp.data['id']


def _approve(client, tid):
    return client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')


# ---------------------------------------------------------------------------
# 五单对称矩阵（审批 → 台账各列变动）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDocumentLedgerMatrix:
    def test_purchase_creates_and_increments_row(self, authenticated_client, branch):
        _ensure_item('MX-P-001')
        tid = _create_doc(authenticated_client, 'purchase', branch, 'MX-P-001', 10)
        assert _approve(authenticated_client, tid).status_code == 200
        row = _row(branch, 'MX-P-001')
        assert row.在库数量 == 10
        # 数量管理品目不生成实例档案（审计 P0-3 守卫）
        from apps.assets.models import FixedAsset
        assert FixedAsset.objects.filter(item__asset_code='MX-P-001').count() == 0
        # 再采购累加
        tid = _create_doc(authenticated_client, 'purchase', branch, 'MX-P-001', 5)
        _approve(authenticated_client, tid)
        assert _row(branch, 'MX-P-001').在库数量 == 15
        assert FixedAsset.objects.filter(item__asset_code='MX-P-001').count() == 0

    def test_purchase_instance_item_generates_instances(self, authenticated_client, branch):
        """实例管理品目采购：台账与实例档案双口径（每件一档，状态在库）。"""
        from apps.assets.models import FixedAsset
        item = _ensure_item('MX-P-INS-001')
        item.management_type = 'instance'
        item.save()
        tid = _create_doc(authenticated_client, 'purchase', branch, 'MX-P-INS-001', 3)
        assert _approve(authenticated_client, tid).status_code == 200
        assert _row(branch, 'MX-P-INS-001').在库数量 == 3
        instances = FixedAsset.objects.filter(item__asset_code='MX-P-INS-001')
        assert instances.count() == 3
        assert all(i.当前状态 == FixedAsset.STATUS_IN_STOCK for i in instances)
        assert all(i.birth_line is not None for i in instances)

    def test_assign_moves_stock_to_in_use(self, authenticated_client, branch):
        _seed(branch, 'MX-A-001', stock=10)
        tid = _create_doc(authenticated_client, 'assign', branch, 'MX-A-001', 3)
        assert _approve(authenticated_client, tid).status_code == 200
        row = _row(branch, 'MX-A-001')
        assert row.在库数量 == 7 and row.在用数量 == 3 and row.总量 == 10

    def test_assign_insufficient_rejected_and_rolled_back(self, authenticated_client, branch):
        _seed(branch, 'MX-A-002', stock=2)
        tid = _create_doc(authenticated_client, 'assign', branch, 'MX-A-002', 3)
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '不足' in str(resp.data['detail'])
        row = _row(branch, 'MX-A-002')
        assert row.在库数量 == 2 and row.在用数量 == 0
        t = Transfer.objects.get(pk=tid)
        assert t.审批状态 == '待审批'  # 单据未生效

    def test_assign_without_row_means_zero_rejected(self, authenticated_client, branch):
        _ensure_item('MX-A-003')
        tid = _create_doc(authenticated_client, 'assign', branch, 'MX-A-003', 1)
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == 400

    def test_return_moves_in_use_to_stock(self, authenticated_client, branch):
        _seed(branch, 'MX-R-001', stock=7, in_use=3)
        tid = _create_doc(
            authenticated_client, 'return', branch, 'MX-R-001', 2, 调入分公司=branch.name,
        )
        assert _approve(authenticated_client, tid).status_code == 200
        row = _row(branch, 'MX-R-001')
        assert row.在用数量 == 1 and row.在库数量 == 9  # 默认回新品在库

    def test_transfer_moves_both_sides(self, authenticated_client, branch, second_branch):
        _seed(branch, 'MX-T-001', stock=10)
        tid = _create_doc(
            authenticated_client, 'transfer', branch, 'MX-T-001', 5,
            调入分公司=second_branch.name,
        )
        assert _approve(authenticated_client, tid).status_code == 200
        assert _row(branch, 'MX-T-001').在库数量 == 5
        dst = _row(second_branch, 'MX-T-001')
        assert dst.在库数量 == 5  # 调入无行则建行

    def test_transfer_insufficient_rejected(self, authenticated_client, branch, second_branch):
        _seed(branch, 'MX-T-002', stock=3)
        tid = _create_doc(
            authenticated_client, 'transfer', branch, 'MX-T-002', 5,
            调入分公司=second_branch.name,
        )
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == 400
        assert not AssetStock.objects.filter(branch=second_branch, item__asset_code='MX-T-002').exists()

    def test_reject_does_not_touch_ledger(self, authenticated_client, branch):
        _seed(branch, 'MX-X-001', stock=10)
        tid = _create_doc(authenticated_client, 'assign', branch, 'MX-X-001', 3)
        resp = authenticated_client.post(
            f'/api/transfers/{tid}/approve', {'approved': False, 'reason': '不需要'}, format='json',
        )
        assert resp.status_code == 200
        row = _row(branch, 'MX-X-001')
        assert row.在库数量 == 10 and row.在用数量 == 0


# ---------------------------------------------------------------------------
# 单据创建校验
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDocumentCreationValidation:
    def test_unregistered_item_uuid_rejected(self, authenticated_client, branch):
        """未登记编号的新形态：items[].item 指向不存在的外键 → 400。"""
        _ensure_item('MX-V-001')
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [{'item': '00000000-0000-0000-0000-000000000000', '数量': 1}],
        }, format='json')
        assert resp.status_code == 400
        assert 'items' in resp.data
        assert any(
            getattr(e, 'code', '') == 'does_not_exist'
            for e in resp.data['items'][0]['item']
        )

    def test_missing_items_rejected(self, authenticated_client, branch):
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
        }, format='json')
        assert resp.status_code == 400
        assert 'items' in resp.data


# ---------------------------------------------------------------------------
# 唯一写入口与调整单
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLedgerAdjustment:
    def test_manual_adjustment_applies_and_traces(self, admin_user, branch):
        from conftest import _client_for
        item = _ensure_item('ADJ-001')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 3, '期初')
        client = _client_for(admin_user)
        resp = client.post('/api/assets/adjustments', {
            'branch': str(branch.id), '资产编号': 'ADJ-001',
            '目标列': '在库数量', '变动量': 5, '事由': '盘点修正',
        }, format='json')
        assert resp.status_code == 201
        assert _row(branch, 'ADJ-001').在库数量 == 8
        adj = LedgerAdjustment.objects.get(item=item, 事由='盘点修正')
        assert adj.变动量 == 5 and adj.is_initial is False

    def test_adjustment_without_permission_rejected(self, staff_user, branch):
        from conftest import _client_for
        _ensure_item('ADJ-002')
        client = _client_for(staff_user)
        resp = client.post('/api/assets/adjustments', {
            'branch': str(branch.id), '资产编号': 'ADJ-002',
            '目标列': '在库数量', '变动量': 1, '事由': 'x',
        }, format='json')
        assert resp.status_code == 403

    def test_adjustment_to_negative_rejected(self, branch):
        from rest_framework.exceptions import ValidationError
        item = _ensure_item('ADJ-003')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 3, '造数')
        with pytest.raises(ValidationError):
            ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, -5, '越界')

    def test_unknown_column_rejected(self, branch):
        from rest_framework.exceptions import ValidationError
        item = _ensure_item('ADJ-004')
        with pytest.raises(ValidationError):
            ledger.apply_adjustment(branch, item, '不存在的列', 1, 'x')

    def test_manual_create_audited_and_numbered(self, admin_user, branch):
        """手动开单：留审计日志，响应带 TZ 编号与空来源。"""
        from conftest import _client_for
        from apps.audit.models import AuditLog
        item = _ensure_item('ADJ-005')
        client = _client_for(admin_user)
        resp = client.post('/api/assets/adjustments', {
            'branch': str(branch.id), '资产编号': 'ADJ-005',
            '目标列': '在库数量', '变动量': 2, '事由': '手工校准',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['单据编号'].startswith('TZ')
        assert resp.data['source_task'] is None
        assert AuditLog.objects.filter(
            action='create', resource_type='LedgerAdjustment',
        ).exists()

    def test_list_filters_by_code_and_branch(self, admin_user, branch):
        from conftest import _client_for
        item = _ensure_item('ADJ-006')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 1, '测试造数')
        client = _client_for(admin_user)
        resp = client.get('/api/assets/adjustments', {'assetCode': 'ADJ-006'})
        assert resp.status_code == 200
        codes = {row['资产编号'] for row in resp.data['results']}
        assert codes == {'ADJ-006'}
        resp = client.get('/api/assets/adjustments', {'assetCode': '不存在的编号'})
        assert resp.data['results'] == []

    def test_numbers_sequential_unique(self, branch):
        item = _ensure_item('ADJ-007')
        numbers = [
            ledger.apply_adjustment(
                branch, item, ledger.COLUMN_STOCK, 1, '测试造数',
            ).单据编号
            for _ in range(3)
        ]
        assert all(n.startswith('TZ') for n in numbers)
        assert len(set(numbers)) == 3

    def test_backfill_migration_idempotent(self, branch):
        """存量回填：空编号行全部补齐、唯一、重跑无副作用。"""
        import importlib
        from django.db import connection
        item = _ensure_item('ADJ-008')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 2, '测试造数')
        LedgerAdjustment.objects.update(单据编号=None)
        migration = importlib.import_module(
            'apps.assets.migrations.0022_backfill_adjustment_doc_no',
        )
        from django.apps import apps as global_apps
        migration.backfill(global_apps, None)
        rows = list(LedgerAdjustment.objects.all())
        assert rows and all(r.单据编号.startswith('TZ') for r in rows)
        assert len({r.单据编号 for r in rows}) == len(rows)
        migration.backfill(global_apps, None)
        assert LedgerAdjustment.objects.count() == len(rows)


@pytest.mark.django_db
class TestConcurrencyGuards:
    def test_double_approve_is_idempotent(self, authenticated_client, branch):
        """同一单据并发/重复审批只生效一次。"""
        _seed(branch, 'CC-001', stock=10)
        tid = _create_doc(authenticated_client, 'assign', branch, 'CC-001', 6)
        assert _approve(authenticated_client, tid).status_code == 200
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == 400
        assert '已审批' in str(resp.data['detail'])
        row = _row(branch, 'CC-001')
        assert row.在库数量 == 4 and row.在用数量 == 6

    def test_second_assign_after_first_exhausts_stock(self, authenticated_client, branch):
        """两单各需 6、在库 10：第一单过后第二单在库不足被拒，不超卖。"""
        _seed(branch, 'CC-002', stock=10)
        tid1 = _create_doc(authenticated_client, 'assign', branch, 'CC-002', 6)
        tid2 = _create_doc(authenticated_client, 'assign', branch, 'CC-002', 6)
        assert _approve(authenticated_client, tid1).status_code == 200
        resp = _approve(authenticated_client, tid2)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        row = _row(branch, 'CC-002')
        assert row.在库数量 == 4 and row.在用数量 == 6


# ---------------------------------------------------------------------------
# Asset 冻结与下游
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAssetRetired:
    def test_main_route_gone(self, authenticated_client):
        """P2 第三刀：Asset 主路由随表退役（summary/fixed-assets 子路由不受影响）。"""
        resp = authenticated_client.get('/api/assets/00000000-0000-0000-0000-000000000000')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestInventoryVarianceAdjustment:
    def _make_task(self, branch, code, stock, entries, name='差异盘点'):
        """entries: [(expected, actual, result), ...]，actual 为 None 表示未盘。"""
        from apps.inventories.models import InventoryTask, InventoryItem
        item = _seed(branch, code, stock=stock)
        row = AssetStock.objects.get(branch=branch, item=item)
        task = InventoryTask.objects.create(name=name, branch=branch, status='pending_review')
        for expected, actual, result in entries:
            InventoryItem.objects.create(
                task=task, stock=row,
                expected_qty=expected, actual_qty=actual, result=result,
            )
        return task, row

    def test_approve_generates_adjustments_for_variance(self, authenticated_client, branch, supervisor_user):
        """审批通过：盘亏开在库 −2 调整单修账，经办人=审批人、来源=任务。"""
        from conftest import _client_for
        task, row = self._make_task(branch, 'INV-001', 5, [(5, 3, 'missing')])
        client = _client_for(supervisor_user)
        resp = client.post(f'/api/inventories/{task.id}/approve')
        assert resp.status_code == 200, resp.data
        row.refresh_from_db()
        assert row.在库数量 == 3
        adj = LedgerAdjustment.objects.get(source_task=task)
        assert adj.目标列 == ledger.COLUMN_STOCK
        assert adj.变动量 == -2
        assert adj.经办人 == supervisor_user
        assert adj.单据编号.startswith('TZ')
        assert task.name in adj.事由 and '在库 5 → 3' in adj.事由

    def test_approve_generates_surplus_adjustment(self, authenticated_client, branch, supervisor_user):
        """盘盈开正量调整单。"""
        from conftest import _client_for
        task, row = self._make_task(branch, 'INV-002', 4, [(4, 6, 'surplus')])
        client = _client_for(supervisor_user)
        resp = client.post(f'/api/inventories/{task.id}/approve')
        assert resp.status_code == 200
        row.refresh_from_db()
        assert row.在库数量 == 6
        assert LedgerAdjustment.objects.get(source_task=task).变动量 == 2

    def test_approve_no_variance_no_adjustment(self, authenticated_client, branch, supervisor_user):
        """全部 matched：审批正常完成，不产调整单。"""
        from conftest import _client_for
        task, row = self._make_task(branch, 'INV-003', 5, [(5, 5, 'matched')])
        client = _client_for(supervisor_user)
        resp = client.post(f'/api/inventories/{task.id}/approve')
        assert resp.status_code == 200
        assert LedgerAdjustment.objects.filter(source_task=task).count() == 0

    def test_approve_insufficient_rolls_back_whole_task(self, authenticated_client, branch, supervisor_user):
        """差异致负数：整笔回滚——任务留 pending_review、台账与调整单零残留。"""
        from conftest import _client_for
        from apps.inventories.models import InventoryTask
        task, row = self._make_task(branch, 'INV-004', 5, [(5, 0, 'missing')])
        # 审批前台账在库被流转单扣到 1：差异 −5 会致负
        row.在库数量 = 1
        row.save(update_fields=['在库数量'])
        client = _client_for(supervisor_user)
        resp = client.post(f'/api/inventories/{task.id}/approve')
        assert resp.status_code == 400
        task.refresh_from_db()
        assert task.status == 'pending_review'
        row.refresh_from_db()
        assert row.在库数量 == 1
        assert LedgerAdjustment.objects.filter(source_task=task).count() == 0

    def test_unchecked_items_not_adjusted(self, authenticated_client, branch, supervisor_user):
        """keep 规则下未盘项（unchecked）与 actual 缺失项不开单。"""
        from conftest import _client_for
        task, row = self._make_task(branch, 'INV-005', 5, [(5, None, 'unchecked')])
        client = _client_for(supervisor_user)
        resp = client.post(f'/api/inventories/{task.id}/approve')
        assert resp.status_code == 200
        row.refresh_from_db()
        assert row.在库数量 == 5
        assert LedgerAdjustment.objects.filter(source_task=task).count() == 0


@pytest.mark.django_db
class TestReportsLedgerBasis:
    def test_reports_follow_ledger(self, authenticated_client, branch):
        _seed(branch, 'RP-001', stock=6, in_use=2, recycle=2)
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.status_code == 200
        assert resp.data['totalAssets'] == 10
        assert resp.data['activeRate'] == 80.0  # (6+2)/10

        resp = authenticated_client.get('/api/reports/by-status/')
        statuses = {r['status']: r['count'] for r in resp.data}
        assert statuses == {'在库': 6, '在用': 2, '回收库': 2}

    def test_purchase_value_from_documents(self, authenticated_client, branch):
        _seed(branch, 'RP-002', stock=1)
        tid = _create_doc(
            authenticated_client, 'purchase', branch, 'RP-002', 2,
            line={'单价': '60.00', '金额': '120.00'},
        )
        assert _approve(authenticated_client, tid).status_code == 200
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.data['totalValue'] == 120
