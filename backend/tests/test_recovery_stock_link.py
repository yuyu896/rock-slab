"""回收单台账联动契约：去向二选一（入回收库 / 直接处置）+ immediate 即时生效。

对应 document-ledger-sync 能力的回收部分；领用/归还/调拨矩阵见 test_ledger_contract.py。
"""
import pytest
from conftest import _client_for
from rest_framework import status

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services import ledger


def _ensure_item(code, management_type='quantity'):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': management_type,
        },
    )
    return item


def _seed_ledger(branch, code, in_use=10, stock=0, management_type='quantity'):
    """经调整单（唯一写入口）造台账底数。"""
    item = _ensure_item(code, management_type)
    if stock:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '测试造数')
    if in_use:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, in_use, '测试造数')
    return AssetStock.objects.get(branch=branch, item=item)


def _recovery_payload(item_id, branch, code, qty=3, instances=None, **overrides):
    """单头 + items 明细行（P2 契约）：品目经字典 uuid 引用，实例引用在明细行 instances。"""
    line = {'item': item_id(code), '数量': qty}
    if instances is not None:
        line['instances'] = [str(pk) for pk in instances]
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
    def test_fa_retired_via_instance_ref_on_approve(self, authenticated_client, branch, item_id):
        """回收绑实例 → 实例转回收库（默认去向），档案保留不删除（P2 第二刀）。"""
        _seed_ledger(branch, 'FAI-1', in_use=2, management_type='instance')
        item = _ensure_item('FAI-1', 'instance')
        inst = FixedAsset.objects.create(
            item=item, 内部编号='FAI-1-1', 当前状态='在用', branch=branch, 使用人='张三',
        )
        resp = authenticated_client.post(
            '/api/transfers/recovery',
            _recovery_payload(item_id, branch, 'FAI-1', qty=1, instances=[inst.pk]),
            format='json',
        )
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        inst.refresh_from_db()
        assert inst.当前状态 == '回收库'
        assert inst.使用人 == ''
        assert FixedAsset.objects.filter(pk=inst.pk).exists()  # 档案保留

    def test_fa_untouched_without_instance_ref(self, authenticated_client, branch, item_id):
        """数量管理品目回收不携带实例，实例档案不受影响。"""
        _seed_ledger(branch, 'RC-6', in_use=2)
        item = _ensure_item('RC-6')
        inst = FixedAsset.objects.create(
            item=item, 内部编号='RC-6-1', 当前状态='在库', branch=branch,
        )
        resp = authenticated_client.post(
            '/api/transfers/recovery', _recovery_payload(item_id, branch, 'RC-6', qty=1), format='json',
        )
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        inst.refresh_from_db()
        assert inst.当前状态 == '在库'


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

    def test_immediate_fa_recovery_retires_instance(self, supervisor_user, branch, item_id):
        """即时回收绑实例 → 立即退役（直接处置），档案保留（P2 第二刀）。"""
        _seed_ledger(branch, 'FAI-2', in_use=1, management_type='instance')
        item = _ensure_item('FAI-2', 'instance')
        inst = FixedAsset.objects.create(
            item=item, 内部编号='FAI-2-1', 当前状态='在用', branch=branch, 使用人='李四',
        )
        client = _client_for(supervisor_user)
        resp = client.post(
            '/api/transfers/recovery',
            _recovery_payload(
                item_id, branch, 'FAI-2', qty=1, instances=[inst.pk],
                immediate=True, 回收去向='dispose', 处置方式='报废',
            ),
            format='json',
        )
        assert resp.status_code == 201
        inst.refresh_from_db()
        assert inst.当前状态 == '退役'
        assert FixedAsset.objects.filter(pk=inst.pk).exists()  # 退役档案永久保留

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
