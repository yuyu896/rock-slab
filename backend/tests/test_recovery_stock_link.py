"""
Tests for recovery → asset summary ledger linkage:
approve-time sync, immediate (row-level) recovery, and non-recovery isolation.
"""
import pytest
from rest_framework import status

from apps.assets.models import Asset, AssetStock, FixedAsset
from conftest import _client_for


def _make_stock(branch, code, qty=10, warning=None, **overrides):
    defaults = dict(
        分公司=branch.name, 分公司编号=branch.code, branch=branch,
        资产编号=code, 资产类目='固定资产', 物品分类='办公设备',
        资产名称=f'物品{code}', 规格='标准', 数量=qty, 警戒线=warning,
    )
    defaults.update(overrides)
    return AssetStock.objects.create(**defaults)


def _make_detail(branch, code, qty=5, dept='', seq=1):
    return Asset.objects.create(
        序号=seq, 分公司=branch.name, 分公司编号=branch.code, branch=branch,
        资产编号=code, 资产类目='固定资产', 物品分类='办公设备',
        资产名称=f'明细{code}', 数量=qty, 所属部门=dept, 当前状态='在库',
    )


def _recovery_payload(branch, code, qty=3, dept='', inner_code='', **overrides):
    data = {
        '调拨日期': '2026-08-19',
        '资产编号': code,
        '资产名称': f'物品{code}',
        '调拨数量': qty,
        '调出分公司': branch.name,
        '调出部门': dept,
        '回收分类': '报废回收',
        'action_type': 'recovery',
    }
    if inner_code:
        data['固定资产内部编号'] = inner_code
    data.update(overrides)
    return data


def _approve(client, pk):
    return client.post(f'/api/transfers/{pk}/approve', {'approved': True})


@pytest.mark.django_db
class TestRecoveryApproveLinkage:
    def test_approve_decrements_ledger_and_recomputes(self, authenticated_client, branch):
        stock = _make_stock(branch, 'RC-1', qty=10, warning=8)
        detail = _make_detail(branch, 'RC-1', qty=6, dept='行政部')

        resp = authenticated_client.post('/api/transfers/recovery', _recovery_payload(branch, 'RC-1', qty=3, dept='行政部'))
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '待审批'
        stock.refresh_from_db()
        assert stock.数量 == 10  # 待审批未联动

        resp = _approve(authenticated_client, resp.data['id'])
        assert resp.status_code == 200
        stock.refresh_from_db()
        assert stock.数量 == 7
        assert stock.是否充足 is False
        detail.refresh_from_db()
        assert detail.数量 == 3

    def test_no_ledger_row_is_tolerated(self, authenticated_client, branch):
        detail = _make_detail(branch, 'RC-2', qty=4)
        resp = authenticated_client.post('/api/transfers/recovery', _recovery_payload(branch, 'RC-2', qty=1))
        assert resp.status_code == 201
        resp = _approve(authenticated_client, resp.data['id'])
        assert resp.status_code == 200
        detail.refresh_from_db()
        assert detail.数量 == 3

    def test_decrement_floors_at_zero(self, authenticated_client, branch):
        stock = _make_stock(branch, 'RC-3', qty=2, warning=1)
        detail = _make_detail(branch, 'RC-3', qty=1, seq=2)
        resp = authenticated_client.post('/api/transfers/recovery', _recovery_payload(branch, 'RC-3', qty=5))
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        stock.refresh_from_db()
        assert stock.数量 == 0
        assert stock.是否充足 is False
        detail.refresh_from_db()
        assert detail.数量 == 0

    def test_detail_kept_when_zeroed(self, authenticated_client, branch):
        detail = _make_detail(branch, 'RC-4', qty=1, seq=3)
        resp = authenticated_client.post('/api/transfers/recovery', _recovery_payload(branch, 'RC-4', qty=9))
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        assert Asset.objects.filter(id=detail.id).exists()
        detail.refresh_from_db()
        assert detail.数量 == 0

    def test_detail_matched_by_department_first(self, authenticated_client, branch):
        _make_stock(branch, 'RC-5', qty=20)
        admin_dept = _make_detail(branch, 'RC-5', qty=4, dept='行政部', seq=4)
        warehouse = _make_detail(branch, 'RC-5', qty=6, dept='仓库', seq=5)
        resp = authenticated_client.post('/api/transfers/recovery', _recovery_payload(branch, 'RC-5', qty=2, dept='行政部'))
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        admin_dept.refresh_from_db()
        warehouse.refresh_from_db()
        assert admin_dept.数量 == 2
        assert warehouse.数量 == 6

    def test_fa_deleted_by_inner_code_on_approve(self, authenticated_client, branch):
        _make_stock(branch, 'RC-6', qty=3)
        fa = FixedAsset.objects.create(
            内部编号='RC-6-1', 资产编号='RC-6', 资产名称='物品RC-6',
            分公司=branch.name, 分公司编号=branch.code, branch=branch,
        )
        resp = authenticated_client.post('/api/transfers/recovery', _recovery_payload(branch, 'RC-6', qty=1, inner_code='RC-6-1'))
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        assert not FixedAsset.objects.filter(id=fa.id).exists()
        stock = AssetStock.objects.get(资产编号='RC-6')
        assert stock.数量 == 2

    def test_fa_untouched_without_inner_code(self, authenticated_client, branch):
        fa = FixedAsset.objects.create(
            内部编号='RC-7-1', 资产编号='RC-7', 资产名称='物品RC-7',
            分公司=branch.name, 分公司编号=branch.code, branch=branch,
        )
        resp = authenticated_client.post('/api/transfers/recovery', _recovery_payload(branch, 'RC-7', qty=1))
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        assert FixedAsset.objects.filter(id=fa.id).exists()

    def test_assign_and_return_do_not_touch_ledger(self, authenticated_client, branch):
        stock = _make_stock(branch, 'RC-8', qty=10)
        detail = _make_detail(branch, 'RC-8', qty=10, seq=6)

        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-19', '资产编号': 'RC-8', '资产名称': '物品RC-8',
            '调拨数量': 2, '调出分公司': branch.name, '调入分公司': branch.name,
            'action_type': 'assign',
        })
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        stock.refresh_from_db()
        assert stock.数量 == 10  # 领用不动台账
        detail.refresh_from_db()
        assert detail.数量 == 8

        resp = authenticated_client.post('/api/transfers/return', {
            '调拨日期': '2026-08-19', '资产编号': 'RC-8', '资产名称': '物品RC-8',
            '调拨数量': 2, '调出分公司': branch.name, '调入分公司': branch.name,
            'action_type': 'return',
        })
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        stock.refresh_from_db()
        assert stock.数量 == 10  # 归还不动台账
        detail.refresh_from_db()
        assert detail.数量 == 10


@pytest.mark.django_db
class TestImmediateRecovery:
    def test_immediate_creates_approved_transfer_and_applies(self, supervisor_user, branch):
        stock = _make_stock(branch, 'IM-1', qty=10, warning=6)
        detail = _make_detail(branch, 'IM-1', qty=5, dept='行政部', seq=7)

        client = _client_for(supervisor_user)
        payload = _recovery_payload(branch, 'IM-1', qty=4, dept='行政部')
        payload['immediate'] = True
        resp = client.post('/api/transfers/recovery', payload)
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '已通过'
        assert resp.data['审批人'] == supervisor_user.name

        stock.refresh_from_db()
        assert stock.数量 == 6
        assert stock.是否充足 is True
        detail.refresh_from_db()
        assert detail.数量 == 1

    def test_immediate_fa_recovery_deletes_record(self, supervisor_user, branch):
        _make_stock(branch, 'IM-2', qty=2)
        fa = FixedAsset.objects.create(
            内部编号='IM-2-1', 资产编号='IM-2', 资产名称='物品IM-2',
            分公司=branch.name, 分公司编号=branch.code, branch=branch,
        )
        client = _client_for(supervisor_user)
        payload = _recovery_payload(branch, 'IM-2', qty=1, inner_code='IM-2-1')
        payload['immediate'] = True
        resp = client.post('/api/transfers/recovery', payload)
        assert resp.status_code == 201
        assert not FixedAsset.objects.filter(id=fa.id).exists()
        stock = AssetStock.objects.get(资产编号='IM-2')
        assert stock.数量 == 1

    def test_immediate_without_manage_assets_rejected(self, staff_user, branch):
        _make_stock(branch, 'IM-3')
        client = _client_for(staff_user)
        payload = _recovery_payload(branch, 'IM-3', qty=1)
        payload['immediate'] = True
        resp = client.post('/api/transfers/recovery', payload)
        assert resp.status_code == 400
        assert '权限' in str(resp.data['detail'])

    def test_immediate_blocked_by_inventory_lock(self, supervisor_user, branch, db):
        from apps.inventories.models import InventoryTask
        InventoryTask.objects.create(name='年度盘点', branch=branch, status='in_progress')
        _make_stock(branch, 'IM-4')
        client = _client_for(supervisor_user)
        payload = _recovery_payload(branch, 'IM-4', qty=1)
        payload['immediate'] = True
        resp = client.post('/api/transfers/recovery', payload)
        assert resp.status_code == 400
        assert '盘点' in str(resp.data)

    def test_immediate_writes_audit_log(self, supervisor_user, branch):
        from apps.audit.models import AuditLog
        _make_stock(branch, 'IM-5')
        client = _client_for(supervisor_user)
        payload = _recovery_payload(branch, 'IM-5', qty=1)
        payload['immediate'] = True
        resp = client.post('/api/transfers/recovery', payload)
        assert resp.status_code == 201
        assert AuditLog.objects.filter(
            description__contains='资产回收', user=supervisor_user,
        ).exists()

    def test_plain_recovery_without_immediate_stays_pending(self, staff_user, branch):
        _make_stock(branch, 'IM-6')
        client = _client_for(staff_user)
        resp = client.post('/api/transfers/recovery', _recovery_payload(branch, 'IM-6', qty=1))
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '待审批'
