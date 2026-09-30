"""inventory-checklist-integrity：启动原子性 / check 行锁与限清单 / 数量非负 / 导入小数拒绝 / 导入确认盘点锁。"""
import io
from unittest import mock

import pytest
from rest_framework import status


def _make_xlsx(headers, rows=None):
    import openpyxl
    from django.core.files.uploadedfile import SimpleUploadedFile
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in (rows or []):
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return SimpleUploadedFile('result.xlsx', buf.getvalue(), content_type='application/vnd.ms-excel')


def _seed_stock(branch, code, qty):
    from apps.assets.services import ledger
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={'asset_category': '完整性测试', 'item_category': '办公',
                  'asset_name': f'品目 {code}', 'unit': '个', 'management_type': 'quantity'},
    )
    ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, qty, '造数')
    return item


def _pending_task(branch, user):
    from apps.inventories.models import InventoryTask
    return InventoryTask.objects.create(
        name='完整性任务', branch=branch, status='pending', created_by=user,
    )


@pytest.mark.django_db
class TestStartAtomicity:
    def test_generation_failure_rolls_back_and_branch_not_locked(
        self, authenticated_client, admin_user, branch,
    ):
        from apps.inventories.models import InventoryTask, InventoryItem
        _seed_stock(branch, 'ICI-1', 5)
        task = _pending_task(branch, admin_user)

        with mock.patch(
            'apps.inventories.views.generate_task_checklist',
            side_effect=RuntimeError('清单生成炸了'),
        ):
            with pytest.raises(RuntimeError):
                authenticated_client.post(f'/api/inventories/{task.id}/start')

        task.refresh_from_db()
        assert task.status == 'pending'
        assert InventoryItem.objects.filter(task=task).count() == 0
        # 分公司不被空清单任务锁死：锁状态解除
        from apps.inventories.models import branch_inventory_locked
        assert branch_inventory_locked(branch) is False

    def test_start_success_generates_checklist_atomically(
        self, authenticated_client, admin_user, branch,
    ):
        from apps.inventories.models import InventoryItem
        _seed_stock(branch, 'ICI-2', 5)
        task = _pending_task(branch, admin_user)
        resp = authenticated_client.post(f'/api/inventories/{task.id}/start')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['status'] == 'in_progress'
        assert InventoryItem.objects.filter(task=task).count() == 1


@pytest.mark.django_db
class TestCheckScoping:
    def test_check_outside_checklist_404(self, authenticated_client, admin_user, branch):
        from apps.assets.models import AssetStock
        from apps.inventories.models import InventoryItem
        from apps.inventories.views import generate_task_checklist
        _seed_stock(branch, 'ICI-3', 5)
        task = _pending_task(branch, admin_user)
        task.status = 'in_progress'
        task.save()
        generate_task_checklist(task)
        # 开始盘点后新出现的台账行（并发残留）不在清单内
        _seed_stock(branch, 'ICI-4', 3)
        stock_b = AssetStock.objects.get(branch=branch, item__asset_code='ICI-4')
        resp = authenticated_client.post(f'/api/inventories/{task.id}/check', {
            'stockId': str(stock_b.id), 'qty': 3,
        }, format='json')
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert '清单' in resp.data['detail']
        assert not InventoryItem.objects.filter(task=task, stock=stock_b).exists()

    def test_check_negative_qty_rejected(self, authenticated_client, admin_user, branch):
        from apps.assets.models import AssetStock
        from apps.inventories.views import generate_task_checklist
        _seed_stock(branch, 'ICI-5', 5)
        task = _pending_task(branch, admin_user)
        task.status = 'in_progress'
        task.save()
        generate_task_checklist(task)
        stock = AssetStock.objects.get(branch=branch, item__asset_code='ICI-5')
        resp = authenticated_client.post(f'/api/inventories/{task.id}/check', {
            'stockId': str(stock.id), 'qty': -2,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestImportResultQuantity:
    _headers = ['序号', '资产编号', '资产名称', '规格', '账面数量', '实盘数量', '备注']

    def _started_task_with_item(self, branch, admin_user, code):
        from apps.assets.models import AssetStock
        from apps.inventories.models import InventoryItem
        from apps.inventories.views import generate_task_checklist
        _seed_stock(branch, code, 5)
        task = _pending_task(branch, admin_user)
        task.status = 'in_progress'
        task.save()
        generate_task_checklist(task)
        return task, InventoryItem.objects.get(
            task=task, stock__item__asset_code=code,
        )

    def test_decimal_qty_rejected(self, authenticated_client, admin_user, branch):
        task, item = self._started_task_with_item(branch, admin_user, 'ICI-6')
        resp = authenticated_client.post(
            f'/api/inventories/{task.id}/import-result',
            {'file': _make_xlsx(self._headers, [[1, 'ICI-6', '品目', '', 5, 2.9, '']])},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert any('必须为整数' in e for e in resp.data['errors'])
        item.refresh_from_db()
        assert item.actual_qty is None and item.result == 'unchecked'

    def test_integer_float_accepted(self, authenticated_client, admin_user, branch):
        task, item = self._started_task_with_item(branch, admin_user, 'ICI-7')
        resp = authenticated_client.post(
            f'/api/inventories/{task.id}/import-result',
            {'file': _make_xlsx(self._headers, [[1, 'ICI-7', '品目', '', 5, 5.0, '']])},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 1
        item.refresh_from_db()
        assert item.actual_qty == 5 and item.result == 'matched'


@pytest.mark.django_db
class TestImportConfirmInventoryLock:
    def _import_file(self, branch, code, qty):
        return _make_xlsx(['分公司', '资产编号', '在库数量'], [[branch.name, code, qty]])

    def test_confirm_blocked_during_inventory_and_recovers(
        self, authenticated_client, admin_user, branch,
    ):
        from apps.assets.models import AssetStock, LedgerAdjustment
        from apps.categories.models import Category
        Category.objects.create(
            asset_category='完整性测试', item_category='办公', asset_name='锁测品目',
            asset_code='ICI-LOCK-1', unit='个',
        )
        AssetStock.objects.create(
            branch=branch,
            item=Category.objects.get(asset_code='ICI-LOCK-1'),
            在库数量=0,
        )
        task = _pending_task(branch, admin_user)
        task.status = 'in_progress'
        task.save()

        blocked = authenticated_client.post('/api/assets/summary/import', {
            'file': self._import_file(branch, 'ICI-LOCK-1', 10),
            'confirm': '1',
        }, format='multipart')
        assert blocked.status_code == status.HTTP_400_BAD_REQUEST
        assert blocked.data['code'] == 'INVENTORY_LOCKED'
        assert branch.name in blocked.data['detail']
        assert AssetStock.objects.get(
            branch=branch, item__asset_code='ICI-LOCK-1',
        ).在库数量 == 0
        assert LedgerAdjustment.objects.count() == 0

        task.status = 'approved'
        task.save()
        ok = authenticated_client.post('/api/assets/summary/import', {
            'file': self._import_file(branch, 'ICI-LOCK-1', 10),
            'confirm': '1',
        }, format='multipart')
        assert ok.status_code == status.HTTP_200_OK
        assert ok.data['applied'] == 1
        assert AssetStock.objects.get(
            branch=branch, item__asset_code='ICI-LOCK-1',
        ).在库数量 == 10
