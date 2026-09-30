"""asset-import-atomicity：台账导入确认整体事务 + 锁内现值复核。"""
import io

import pytest
from rest_framework import status

from apps.assets.models import AssetStock, LedgerAdjustment


def _xlsx_bytes(header, rows):
    import openpyxl
    from django.core.files.uploadedfile import SimpleUploadedFile
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return SimpleUploadedFile('import.xlsx', buf.getvalue(), content_type='application/vnd.ms-excel')


def _ensure_item(code):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '原子性测试', 'item_category': '办公',
            'asset_name': f'品目 {code}', 'unit': '件', 'management_type': 'quantity',
        },
    )
    return item


def _grant(user, code):
    from apps.permissions.models import OperationGrant
    OperationGrant.objects.get_or_create(user=user, code=code)


@pytest.mark.django_db
class TestImportAtomicity:
    def _file(self, rows):
        return _xlsx_bytes(['分公司', '资产编号', '在库数量'], rows)

    def test_midway_failure_rolls_back_all(self, manager_user, branch):
        """行2 应用失败（联动后为负）→ 行1 也回滚，无调整单残留。"""
        from conftest import _client_for
        _grant(manager_user, 'adjust_ledger')
        item_a = _ensure_item('ATOM-1')
        item_b = _ensure_item('ATOM-2')
        # 底数：A 行 5（导入 10，delta +5）；B 行 0（导入 -3 → 联动后为负必炸）
        from apps.assets.services import ledger
        ledger.apply_adjustment(branch, item_a, ledger.COLUMN_STOCK, 5, '造数')
        client = _client_for(manager_user)
        resp = client.post('/api/assets/summary/import', {
            'file': self._file([
                [branch.name, 'ATOM-1', 10],
                [branch.name, 'ATOM-2', -3],
            ]),
            'confirm': '1',
        }, format='multipart')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data['code'] == 'LEDGER_INSUFFICIENT'
        # 整体回滚：行1 未应用，无任何导入调整单
        assert AssetStock.objects.get(branch=branch, item=item_a).在库数量 == 5
        assert not AssetStock.objects.filter(branch=branch, item=item_b).exists()
        assert LedgerAdjustment.objects.count() == 1  # 仅造数那一张

    def test_stale_current_value_rejected(self, manager_user, branch):
        """请求内并发窗口：解析后、应用前现值被改 → IMPORT_STALE，台账保持并发值。

        导入为无状态两阶段（confirm 请求内重新解析），竞态窗口在解析→应用之间；
        用 mock 在解析返回后注入变动以确定性复现。
        """
        from unittest import mock
        from conftest import _client_for
        from apps.assets.views import AssetStockViewSet
        _grant(manager_user, 'adjust_ledger')
        item = _ensure_item('ATOM-3')
        AssetStock.objects.create(branch=branch, item=item, 在库数量=0)
        client = _client_for(manager_user)

        original_parse = AssetStockViewSet._parse_import_rows

        def parse_then_concurrent_change(self, f, user):
            diffs, errors = original_parse(self, f, user)
            # 模拟解析完成后、应用前的并发变动：现值 0 → 100
            AssetStock.objects.filter(branch=branch, item=item).update(在库数量=100)
            return diffs, errors

        with mock.patch.object(
            AssetStockViewSet, '_parse_import_rows', parse_then_concurrent_change,
        ):
            resp = client.post('/api/assets/summary/import', {
                'file': self._file([[branch.name, 'ATOM-3', 10]]),
                'confirm': '1',
            }, format='multipart')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data['code'] == 'IMPORT_STALE'
        assert 'ATOM-3' in str(resp.data['detail'])
        # 台账保持并发后的值，不被导入覆盖
        assert AssetStock.objects.get(branch=branch, item=item).在库数量 == 100
        assert LedgerAdjustment.objects.count() == 0

    def test_normal_confirm_applies_all(self, manager_user, branch):
        from conftest import _client_for
        _grant(manager_user, 'adjust_ledger')
        item_a = _ensure_item('ATOM-4')
        item_b = _ensure_item('ATOM-5')
        client = _client_for(manager_user)
        resp = client.post('/api/assets/summary/import', {
            'file': self._file([
                [branch.name, 'ATOM-4', 10],
                [branch.name, 'ATOM-5', 7],
            ]),
            'confirm': '1',
        }, format='multipart')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['applied'] == 2
        assert AssetStock.objects.get(branch=branch, item=item_a).在库数量 == 10
        assert AssetStock.objects.get(branch=branch, item=item_b).在库数量 == 7
        assert LedgerAdjustment.objects.count() == 2

    def test_reupload_after_confirm_no_double_apply(self, manager_user, branch):
        """同文件二次确认：无状态重解析差量为零 → applied=0 幂等，无二次变动。"""
        from conftest import _client_for
        _grant(manager_user, 'adjust_ledger')
        item = _ensure_item('ATOM-6')
        client = _client_for(manager_user)
        first = client.post('/api/assets/summary/import', {
            'file': self._file([[branch.name, 'ATOM-6', 10]]),
            'confirm': '1',
        }, format='multipart')
        assert first.status_code == status.HTTP_200_OK
        assert first.data['applied'] == 1
        second = client.post('/api/assets/summary/import', {
            'file': self._file([[branch.name, 'ATOM-6', 10]]),
            'confirm': '1',
        }, format='multipart')
        assert second.status_code == status.HTTP_200_OK
        assert second.data['applied'] == 0
        assert AssetStock.objects.get(branch=branch, item=item).在库数量 == 10
        assert LedgerAdjustment.objects.count() == 1
