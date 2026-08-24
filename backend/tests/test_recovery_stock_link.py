"""回收单台账联动契约：去向二选一（入回收库 / 直接处置）+ immediate 即时生效。

对应 document-ledger-sync 能力的回收部分；领用/归还/调拨矩阵见 test_ledger_contract.py。
"""
import pytest
from conftest import _client_for
from rest_framework import status

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services import ledger


def _ensure_item(code):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
        },
    )
    return item


def _seed_ledger(branch, code, in_use=10, stock=0):
    """经调整单（唯一写入口）造台账底数。"""
    item = _ensure_item(code)
    if stock:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '测试造数')
    if in_use:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, in_use, '测试造数')
    return AssetStock.objects.get(branch=branch, item=item)


def _recovery_payload(item_id, branch, code, qty=3, inner_code='', **overrides):
    """单头 + items 明细行（P2 契约）：品目经字典 uuid 引用，回收行内字段在明细行上。"""
    line = {'item': item_id(code), '数量': qty}
    if inner_code:
        line['固定资产内部编号'] = inner_code
    payload = {
        '调拨日期': '2026-08-23',
        '调出分公司': branch.name,
        'items': [line],
    }
    payload.update(overrides)
    return payload


def _approve(client, pk):
    return client.post(f'/api/transfers/{pk}/approve', {'approved': True}, format='json')


def _row(branch, code):
    return AssetStock.objects.get(branch=branch, item__asset_code=code)


@pytest.mark.django_db
class TestRecoveryToRecycleBin:
    def test_approve_moves_in_use_to_recycle(self, authenticated_client, branch, item_id):
        _seed_ledger(branch, 'RC-1', in_use=10)
        resp = authenticated_client.post(
            '/api/transfers/recovery', _recovery_payload(item_id, branch, 'RC-1', qty=3), format='json',
        )
        assert resp.status_code == 201
        resp = _approve(authenticated_client, resp.data['id'])
        assert resp.status_code == 200
        row = _row(branch, 'RC-1')
        assert row.在用数量 == 7
        assert row.回收库数量 == 3
        assert row.总量 == 10

    def test_insufficient_in_use_rejected(self, authenticated_client, branch, item_id):
        _seed_ledger(branch, 'RC-2', in_use=2, stock=50)
        resp = authenticated_client.post(
            '/api/transfers/recovery', _recovery_payload(item_id, branch, 'RC-2', qty=5), format='json',
        )
        assert resp.status_code == 201
        resp = _approve(authenticated_client, resp.data['id'])
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '不足' in str(resp.data['detail'])
        row = _row(branch, 'RC-2')
        assert row.在用数量 == 2 and row.回收库数量 == 0  # 整体回滚


@pytest.mark.django_db
class TestRecoveryDirectDispose:
    def test_dispose_drops_total_without_recycle(self, authenticated_client, branch, item_id):
        _seed_ledger(branch, 'RC-3', in_use=6, stock=4)
        resp = authenticated_client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'RC-3', qty=2, 回收去向='dispose', 处置方式='出售', 处置金额=500),
            format='json',
        )
        assert resp.status_code == 201
        tid = resp.data['id']
        assert resp.data['回收去向'] == 'dispose'
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == 200
        row = _row(branch, 'RC-3')
        assert row.在用数量 == 4
        assert row.回收库数量 == 0  # 直接处置不入回收库
        assert row.总量 == 8  # 4 在库 + 4 在用，总量随处置下跌

    def test_dispose_requires_no_amount_but_records_when_sold(self, authenticated_client, branch, item_id):
        _seed_ledger(branch, 'RC-4', in_use=3)
        resp = authenticated_client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'RC-4', qty=1, 回收去向='dispose', 处置方式='报废'),
            format='json',
        )
        assert resp.status_code == 201
        assert resp.data['处置方式'] == '报废'


@pytest.mark.django_db
class TestRecoveryFixedAsset:
    def test_fa_deleted_by_inner_code_on_approve(self, authenticated_client, branch, item_id):
        _seed_ledger(branch, 'RC-5', in_use=2)
        FixedAsset.objects.create(
            内部编号='RC-5-1', 资产编号='RC-5', 资产名称='实例RC-5',
            分公司=branch.name, 分公司编号=branch.code, branch=branch,
        )
        resp = authenticated_client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'RC-5', qty=1, inner_code='RC-5-1'),
            format='json',
        )
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        assert not FixedAsset.objects.filter(内部编号='RC-5-1').exists()

    def test_fa_untouched_without_inner_code(self, authenticated_client, branch, item_id):
        _seed_ledger(branch, 'RC-6', in_use=2)
        FixedAsset.objects.create(
            内部编号='RC-6-1', 资产编号='RC-6', 资产名称='实例RC-6',
            分公司=branch.name, 分公司编号=branch.code, branch=branch,
        )
        resp = authenticated_client.post(
            '/api/transfers/recovery', _recovery_payload(item_id, branch, 'RC-6', qty=1), format='json',
        )
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        assert FixedAsset.objects.filter(内部编号='RC-6-1').exists()


@pytest.mark.django_db
class TestImmediateRecovery:
    def test_immediate_applies_recycle_bin(self, supervisor_user, branch, item_id):
        _seed_ledger(branch, 'IM-1', in_use=5)
        client = _client_for(supervisor_user)
        resp = client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'IM-1', qty=2, immediate=True),
            format='json',
        )
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '已通过'
        row = _row(branch, 'IM-1')
        assert row.在用数量 == 3 and row.回收库数量 == 2

    def test_immediate_dispose(self, supervisor_user, branch, item_id):
        _seed_ledger(branch, 'IM-2', in_use=5)
        client = _client_for(supervisor_user)
        resp = client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'IM-2', qty=2, immediate=True, 回收去向='dispose'),
            format='json',
        )
        assert resp.status_code == 201
        row = _row(branch, 'IM-2')
        assert row.在用数量 == 3 and row.回收库数量 == 0

    def test_immediate_fa_recovery_deletes_record(self, supervisor_user, branch, item_id):
        _seed_ledger(branch, 'IM-3', in_use=1)
        FixedAsset.objects.create(
            内部编号='IM-3-1', 资产编号='IM-3', 资产名称='实例IM-3',
            分公司=branch.name, 分公司编号=branch.code, branch=branch,
        )
        client = _client_for(supervisor_user)
        resp = client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'IM-3', qty=1, inner_code='IM-3-1', immediate=True),
            format='json',
        )
        assert resp.status_code == 201
        assert not FixedAsset.objects.filter(内部编号='IM-3-1').exists()

    def test_immediate_without_manage_assets_rejected(self, staff_user, branch, item_id):
        _seed_ledger(branch, 'IM-4', in_use=5)
        client = _client_for(staff_user)
        resp = client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'IM-4', qty=1, immediate=True),
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '权限' in str(resp.data['detail'])

    def test_immediate_blocked_by_inventory_lock(self, supervisor_user, branch, item_id, db):
        from apps.inventories.models import InventoryTask
        _seed_ledger(branch, 'IM-5', in_use=5)
        InventoryTask.objects.create(
            name='锁库盘点', branch=branch, status='in_progress',
        )
        client = _client_for(supervisor_user)
        resp = client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'IM-5', qty=1, immediate=True),
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '盘点' in str(resp.data['detail'])

    def test_plain_recovery_without_immediate_stays_pending(self, staff_user, branch, item_id):
        _seed_ledger(branch, 'IM-6', in_use=5)
        client = _client_for(staff_user)
        resp = client.post(
            '/api/transfers/recovery', _recovery_payload(item_id, branch, 'IM-6', qty=1), format='json',
        )
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '待审批'
        row = _row(branch, 'IM-6')
        assert row.在用数量 == 5  # 未审批不动账
