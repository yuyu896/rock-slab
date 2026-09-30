"""approve-inventory-lock-recheck：盘点锁定期间流转审批必须被拒（与创建闸对称）。"""
import pytest
from rest_framework import status

from apps.assets.models import AssetStock
from apps.categories.models import Category
from apps.inventories.models import InventoryTask
from apps.transfers.models import Transfer


def _item(code):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '电子设备', 'item_category': '电脑',
            'asset_name': f'品目 {code}', 'unit': '台', 'management_type': 'ledger',
        },
    )
    return item


def _purchase(client, item, branch):
    resp = client.post('/api/transfers/purchase', {
        '调拨日期': '2026-09-30', '调入分公司': branch.name,
        'items': [{'item': str(item.id), '数量': 3}],
    }, format='json')
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return resp.data['id']


@pytest.mark.django_db
class TestApproveInventoryLockRecheck:
    def test_purchase_approve_blocked_during_inventory(self, manager_user, branch):
        from conftest import _client_for
        client = _client_for(manager_user)
        item = _item('AIL-1')
        tid = _purchase(client, item, branch)
        InventoryTask.objects.create(
            name='年中盘点', branch=branch, status='in_progress', created_by=manager_user,
        )
        resp = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data['code'] == 'INVENTORY_LOCKED'
        assert not AssetStock.objects.filter(item=item, branch=branch).exists()
        assert Transfer.objects.get(id=tid).审批状态 == '待审批'

    def test_transfer_approve_blocked_when_to_side_locked(self, manager_user, branch, second_branch):
        from conftest import _client_for
        client = _client_for(manager_user)
        item = _item('AIL-2')
        assert client.post(
            f"/api/transfers/{_purchase(client, item, branch)}/approve",
            {'approved': True}, format='json',
        ).status_code == status.HTTP_200_OK
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-09-30',
            '调出分公司': branch.name, '调入分公司': second_branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        tid = resp.data['id']
        InventoryTask.objects.create(
            name='调入方盘点', branch=second_branch, status='in_progress', created_by=manager_user,
        )
        resp2 = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST
        assert resp2.data['code'] == 'INVENTORY_LOCKED'
        assert AssetStock.objects.get(item=item, branch=branch).在库数量 == 3
        assert not AssetStock.objects.filter(item=item, branch=second_branch).exists()

    def test_unrelated_branch_inventory_allows_approve(self, manager_user, branch, second_branch):
        from conftest import _client_for
        client = _client_for(manager_user)
        item = _item('AIL-3')
        tid = _purchase(client, item, branch)
        InventoryTask.objects.create(
            name='别家盘点', branch=second_branch, status='in_progress', created_by=manager_user,
        )
        resp = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert AssetStock.objects.get(item=item, branch=branch).在库数量 == 3

    def test_approve_succeeds_after_inventory_done(self, manager_user, branch):
        from conftest import _client_for
        client = _client_for(manager_user)
        item = _item('AIL-4')
        tid = _purchase(client, item, branch)
        task = InventoryTask.objects.create(
            name='短盘点', branch=branch, status='in_progress', created_by=manager_user,
        )
        blocked = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert blocked.status_code == status.HTTP_400_BAD_REQUEST
        task.status = 'approved'
        task.save()
        resp = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert AssetStock.objects.get(item=item, branch=branch).在库数量 == 3
