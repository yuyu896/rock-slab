"""P1 台账契约测试：五单对称矩阵、唯一写入口、调整单、Asset 冻结、报表口径。

对应 document-ledger-sync / ledger-single-source / asset-freeze-readonly 能力。
"""
import pytest
from rest_framework import status

from apps.assets.models import Asset, AssetStock, LedgerAdjustment
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


def _create_doc(client, action, branch, code, qty, **extra):
    payload = {
        '调拨日期': '2026-08-23',
        '资产编号': code,
        '资产名称': f'品目 {code}',
        '调拨数量': qty,
        '调出分公司': branch.name,
    }
    payload.update(extra)
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
        # 再采购累加
        tid = _create_doc(authenticated_client, 'purchase', branch, 'MX-P-001', 5)
        _approve(authenticated_client, tid)
        assert _row(branch, 'MX-P-001').在库数量 == 15

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
    def test_unregistered_code_rejected_with_suggestion(self, authenticated_client, branch):
        _ensure_item('MX-V-001')
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '资产编号': 'MX-V-001X', '资产名称': '未登记',
            '调拨数量': 1, '调出分公司': branch.name,
        }, format='json')
        assert resp.status_code == 400
        assert '未在品目字典登记' in str(resp.data['detail'])

    def test_missing_code_rejected(self, authenticated_client, branch):
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '资产名称': '无编号', '调拨数量': 1,
            '调出分公司': branch.name,
        }, format='json')
        assert resp.status_code == 400


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
class TestAssetFreeze:
    def test_write_endpoints_return_405(self, authenticated_client, branch):
        _ensure_item('FZ-001')
        resp = authenticated_client.post('/api/assets/', {
            '分公司': branch.name, '资产编号': 'FZ-001', '资产类目': 'a', '物品分类': 'b',
            '资产名称': 'x', '数量': 1,
        }, format='json')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_import_returns_410(self, authenticated_client):
        import io
        resp = authenticated_client.post('/api/assets/import', {'file': io.BytesIO(b'x')}, format='multipart')
        assert resp.status_code == status.HTTP_410_GONE

    def test_list_still_readable(self, authenticated_client, branch):
        Asset.objects.create(
            序号=1, 分公司=branch.name, 分公司编号=branch.code, branch=branch,
            资产编号='FZ-002', 资产类目='a', 物品分类='b', 资产名称='历史', 数量=2, 当前状态='在库',
        )
        resp = authenticated_client.get('/api/assets/')
        assert resp.status_code == 200

    def test_assign_approval_leaves_asset_untouched(self, authenticated_client, branch):
        asset = Asset.objects.create(
            序号=2, 分公司=branch.name, 分公司编号=branch.code, branch=branch,
            资产编号='FZ-003', 资产类目='a', 物品分类='b', 资产名称='冻结', 数量=5, 当前状态='在库',
        )
        _seed(branch, 'FZ-003', stock=10)
        tid = _create_doc(authenticated_client, 'assign', branch, 'FZ-003', 3)
        assert _approve(authenticated_client, tid).status_code == 200
        asset.refresh_from_db()
        assert asset.数量 == 5 and asset.当前状态 == '在库'  # Asset 零变化


@pytest.mark.django_db
class TestInventoryRecordMode:
    def test_approve_keeps_asset_quantities(self, authenticated_client, branch, supervisor_user):
        """盘点审核通过仅记录差异，不再改 Asset 数量。"""
        from conftest import _client_for
        from apps.inventories.models import InventoryTask, InventoryItem
        asset = Asset.objects.create(
            序号=3, 分公司=branch.name, 分公司编号=branch.code, branch=branch,
            资产编号='INV-001', 资产类目='测试类目', 物品分类='测试分类',
            资产名称='盘点物', 数量=5, 当前状态='在库',
        )
        task = InventoryTask.objects.create(name='记录模式盘点', branch=branch, status='pending_review')
        InventoryItem.objects.create(
            task=task, asset=asset, expected_qty=5, actual_qty=3, result='discrepancy',
        )
        client = _client_for(supervisor_user)
        resp = client.post(f'/api/inventories/{task.id}/approve')
        assert resp.status_code == 200
        asset.refresh_from_db()
        assert asset.数量 == 5  # 不再直改


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
        from decimal import Decimal
        _seed(branch, 'RP-002', stock=1)
        tid = _create_doc(
            authenticated_client, 'purchase', branch, 'RP-002', 2,
            总金额=Decimal('120.00'),
        )
        assert _approve(authenticated_client, tid).status_code == 200
        resp = authenticated_client.get('/api/reports/overview/')
        assert resp.data['totalValue'] == 120
