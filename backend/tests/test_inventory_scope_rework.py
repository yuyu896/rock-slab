"""
Tests for inventory-scope-rework：盘点范围按品目管理方式分派（第一步：盘点线）。
"""
import io

import openpyxl
import pytest
from rest_framework import status

from apps.assets.models import FixedAsset
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.inventories.models import InventoryTask, InventoryInstanceItem, InventoryItem
from apps.organizations.models import Department


def _item(code, management_type='instance', asset_category='电子设备'):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': asset_category, 'item_category': '电脑',
            'asset_name': f'品目 {code}', 'unit': '台',
            'management_type': management_type,
        },
    )
    return item


def _mk_inst(branch, item, no, state='在库'):
    return FixedAsset.objects.create(
        item=item, 内部编号=f'{item.asset_code}-{branch.code}-{no}',
        当前状态=state, branch=branch,
        使用人='张三' if state == '在用' else '',
    )


def _task(branch, kind='instance', category=None):
    return InventoryTask.objects.create(
        name='范围测试盘', kind=kind, branch=branch, category=category,
        stock_bin='stock', missed_rule='zero', repeat_rule='last',
    )


@pytest.mark.django_db
class TestInstanceScopeFullArchive:
    def test_weifang_shape_all_stock_instances_includable(self, authenticated_client, branch):
        """潍坊形态：全在库（0 在用）可开始实例盘，清单含在库实例。"""
        item = _item('WF-1')
        for i in range(3):
            _mk_inst(branch, item, i, state='在库')
        task = _task(branch, kind='instance')
        resp = authenticated_client.post(f'/api/inventories/{task.id}/start')
        assert resp.status_code == status.HTTP_200_OK
        assert task.instance_items.count() == 3

    def test_retired_excluded(self, authenticated_client, branch):
        item = _item('WF-2')
        _mk_inst(branch, item, 1, state='在库')
        _mk_inst(branch, item, 2, state='在用')
        _mk_inst(branch, item, 3, state='退役')
        task = _task(branch, kind='instance')
        resp = authenticated_client.post(f'/api/inventories/{task.id}/start')
        assert resp.status_code == status.HTTP_200_OK
        assert task.instance_items.count() == 2  # 退役不进快照

    def test_jining_shape_89_all_in_one_sheet(self, authenticated_client, branch, item_id):
        """济宁形态：89 台全量（在库+在用）全进清单，导入全量零错。"""
        item = _item('JN-1')
        for i in range(2):
            _mk_inst(branch, item, i, state='在库')
        for i in range(2, 4):
            _mk_inst(branch, item, i, state='在用')
        task = _task(branch, kind='instance')
        assert authenticated_client.post(f'/api/inventories/{task.id}/start').status_code == 200
        assert task.instance_items.count() == 4
        headers = ['序号', '内部编号', '序列号', '品目编号', '品目名称', '状态', '使用人', '所属部门', '核对结果', '备注']
        rows = []
        for idx, entry in enumerate(task.instance_items.select_related('instance'), start=1):
            rows.append([idx, entry.instance.内部编号, '', item.asset_code, item.asset_name,
                         '在库', '', '', '已找到', ''])
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(headers)
        for r in rows:
            ws.append(r)
        buf = io.BytesIO(); wb.save(buf); buf.seek(0); buf.name = 't.xlsx'
        resp = authenticated_client.post(
            f'/api/inventories/{task.id}/import-result', {'file': buf}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 4 and not resp.data['errors']

    def test_old_template_without_status_rejected(self, authenticated_client, branch):
        """旧版 9 列模板（无状态列）被表头守卫拦下。"""
        item = _item('JN-2')
        _mk_inst(branch, item, 1)
        task = _task(branch, kind='instance')
        assert authenticated_client.post(f'/api/inventories/{task.id}/start').status_code == 200
        headers = ['序号', '内部编号', '序列号', '品目编号', '品目名称', '使用人', '所属部门', '核对结果', '备注']
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(headers)
        ws.append([1, f'{item.asset_code}-{task.branch.code}-1', '', item.asset_code, item.asset_name, '', '', '已找到', ''])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0); buf.name = 't.xlsx'
        resp = authenticated_client.post(
            f'/api/inventories/{task.id}/import-result', {'file': buf}, format='multipart')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '重新下载' in str(resp.data['detail'])


@pytest.mark.django_db
class TestStockScopeNonInstance:
    def test_instance_items_excluded_from_stock_inventory(self, authenticated_client, branch):
        """济宁形态：实例品目不进台账盘，数量品目按总量应盘。"""
        inst_item = _item('ST-1', 'instance')
        for i in range(3):
            _mk_inst(branch, inst_item, i, state='在库')
        qty_item = _item('ST-2', 'quantity')
        ledger.apply_adjustment(branch, qty_item, ledger.COLUMN_STOCK, 7, '造数')
        ledger.apply_adjustment(branch, qty_item, ledger.COLUMN_IN_USE, 2, '造数')
        task = _task(branch, kind='stock')
        resp = authenticated_client.post(f'/api/inventories/{task.id}/start')
        assert resp.status_code == status.HTTP_200_OK
        items = task.items.select_related('stock__item')
        assert items.count() == 1
        assert items.first().stock.item.asset_code == 'ST-2'
        assert items.first().expected_qty == 9  # 总量 = 在库7+在用2

    def test_variance_adjusts_stock_with_inuse_hint(self, authenticated_client, branch):
        """差异调整单扣在库列；在用余额品目差异行备注提示人工核实。"""
        from apps.inventories.services import generate_variance_adjustments
        qty_item = _item('ST-3', 'quantity')
        ledger.apply_adjustment(branch, qty_item, ledger.COLUMN_STOCK, 10, '造数')
        ledger.apply_adjustment(branch, qty_item, ledger.COLUMN_IN_USE, 5, '造数')
        task = _task(branch, kind='stock')
        assert authenticated_client.post(f'/api/inventories/{task.id}/start').status_code == 200
        entry = task.items.select_related('stock').first()
        assert entry.expected_qty == 15
        # 实盘 13 → 盘亏 2
        entry.actual_qty = 13
        entry.result = 'missing'
        entry.save(update_fields=['actual_qty', 'result'])
        from django.contrib.auth import get_user_model
        admin = get_user_model().objects.filter(phone='13900000000').first() or get_user_model().objects.create_user(
            phone='13900000009', name='审批人', password='x', role='admin', status='active')
        adjs = generate_variance_adjustments(task, admin)
        assert len(adjs) == 1
        entry.refresh_from_db()
        stock = entry.stock.select_related if False else entry.stock
        stock.refresh_from_db()
        assert stock.在库数量 == 8  # 10-2 扣在库
        assert '在用量 5' in entry.remarks and '人工核实' in entry.remarks


@pytest.mark.django_db
class TestReportInstanceStatus:
    def test_report_items_carry_instance_status(self, authenticated_client, branch):
        """报告项含 instanceStatus（前端在库/在用区分与一键回收过滤依据）。"""
        item = _item('RP-1')
        _mk_inst(branch, item, 1, state='在库')
        _mk_inst(branch, item, 2, state='在用')
        task = _task(branch, kind='instance')
        assert authenticated_client.post(f'/api/inventories/{task.id}/start').status_code == 200
        resp = authenticated_client.get(f'/api/inventories/{task.id}/report')
        assert resp.status_code == 200
        statuses = {i['instance_code']: i['instance_status'] for i in resp.data['items']}
        assert statuses[f'RP-1-{branch.code}-1'] == '在库'
        assert statuses[f'RP-1-{branch.code}-2'] == '在用'

    def test_template_status_column_filled(self, authenticated_client, branch):
        item = _item('RP-2')
        _mk_inst(branch, item, 1, state='在库')
        _mk_inst(branch, item, 2, state='在用')
        task = _task(branch, kind='instance')
        assert authenticated_client.post(f'/api/inventories/{task.id}/start').status_code == 200
        resp = authenticated_client.get(f'/api/inventories/{task.id}/import-template')
        ws = openpyxl.load_workbook(io.BytesIO(resp.content)).active
        assert ws['F1'].value == '状态'
        assert {ws['F2'].value, ws['F3'].value} == {'在库', '在用'}
