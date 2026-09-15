"""
Comprehensive tests for all import/export/template endpoints across 7 modules.
Covers: FixedAsset, Category, Transfer (4 types), Inventory.
"""
import io
import pytest
from datetime import date

import openpyxl
from rest_framework import status

from conftest import _client_for


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_xlsx(headers, rows=None):
    """Build an in-memory Excel file with given headers and rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in (rows or []):
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = 'test.xlsx'
    return buf


def _parse_excel_response(response):
    """Parse an Excel response into (headers, rows)."""
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    ws = wb.active
    data = list(ws.iter_rows(values_only=True))
    headers = list(data[0]) if data else []
    rows = [list(r) for r in data[1:]] if len(data) > 1 else []
    return headers, rows


def _upload_url(client, url, buf, params=None):
    """Upload an Excel buffer to the given URL."""
    return client.post(url, {'file': buf}, format='multipart', QUERY_STRING=params or '')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_client(admin_user):
    return _client_for(admin_user)


@pytest.fixture
def test_branch(db):
    from apps.organizations.models import Region, Team, Branch
    region = Region.objects.create(name='测试区域', code='TEST', status='active')
    team = Team.objects.create(name='测试行政组', region=region, status='active')
    branch = Branch.objects.create(
        name='测试分公司', code='TB001', team=team,
        address='测试地址', phone='010-12345678',
    )
    return branch


@pytest.fixture
def test_category(db):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='测试类目', item_category='测试分类',
        asset_name='测试资产', asset_code='TC001', unit='台',
    )


@pytest.fixture
def ta001_category(db):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='测试类目', item_category='测试分类',
        asset_name='测试资产', asset_code='TA001', unit='台',
    )


# ===========================================================================
# 2. Asset module
# ===========================================================================

# ===========================================================================
# 2. FixedAsset module
# ===========================================================================

class TestFixedAssetEndpointsFrozen:
    """P2 第二刀：实例导入/模板下线——出生=采购单，存量=迁移。"""

    def test_template_endpoint_gone(self, admin_client):
        resp = admin_client.get('/api/assets/fixed-assets/template')
        assert resp.status_code in (404, 410)

    def test_import_endpoint_gone(self, admin_client):
        buf = _make_xlsx(['资产编号', '名称'], [['TA001', 'x']])
        resp = _upload_url(admin_client, '/api/assets/fixed-assets/import', buf)
        assert resp.status_code == status.HTTP_410_GONE
        assert '采购入库单' in resp.data['detail']


# ===========================================================================
# 4. Category module
# ===========================================================================

CATEGORY_TEMPLATE_HEADERS = ['资产类目', '物品分类', '资产名称', '资产编号', '计量单位', '警戒线', '备注']
CATEGORY_EXPORT_HEADERS = ['资产类目', '物品分类', '资产名称', '资产编号', '计量单位', '资产数量', '在库数量', '警戒线', '备注']


class TestCategoryTemplate:
    def test_download_template(self, admin_client):
        resp = admin_client.get('/api/categories/template')
        headers, rows = _parse_excel_response(resp)
        assert rows == []
        for h in CATEGORY_TEMPLATE_HEADERS:
            assert h in headers, f"Missing header: {h}"


class TestCategoryImport:
    def test_import_valid_data(self, admin_client):
        rows = [
            ['办公类', '电子设备', '笔记本电脑', 'CAT-L001', '台', 10, '办公用'],
            ['办公类', '家具', '办公桌', 'CAT-D001', '张', '', ''],
        ]
        buf = _make_xlsx(CATEGORY_TEMPLATE_HEADERS, rows)
        resp = _upload_url(admin_client, '/api/categories/import', buf)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 2
        from apps.categories.models import Category
        c = Category.objects.get(asset_code='CAT-L001')
        assert c.asset_name == '笔记本电脑'
        assert c.unit == '台'

    def test_import_duplicate_asset_code_updates(self, admin_client, test_category):
        """Category import uses update_or_create, so duplicate asset_code should update."""
        rows = [
            ['更新类目', '更新分类', '更新资产', test_category.asset_code, '套', '', ''],
        ]
        buf = _make_xlsx(CATEGORY_TEMPLATE_HEADERS, rows)
        resp = _upload_url(admin_client, '/api/categories/import', buf)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 1
        test_category.refresh_from_db()
        assert test_category.asset_name == '更新资产'
        assert test_category.unit == '套'


def _make_xlsx_multi(sheets):
    """Build an in-memory Excel with multiple named sheets: {name: [rows]}."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        ws.append(CATEGORY_TEMPLATE_HEADERS)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = 'test.xlsx'
    return buf


class TestCategoryImportBySheet:
    """sheet 名定管理方式（category-import-by-sheet）。"""

    def test_three_sheets_in_one_file(self, admin_client):
        buf = _make_xlsx_multi({
            '数量管理': [['固定资产类', '办公设备', '打印机', 'A-a00002', '个', 1, '']],
            '实例管理': [['固定资产类', '办公设备', '平板电脑', 'A-a00001', '个', 1, '']],
            '消耗品': [['低值易耗品类', '办公耗材', '打印纸', 'B-b00001', '包', 1, '']],
        })
        resp = _upload_url(admin_client, '/api/categories/import', buf)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 3
        assert resp.data['fallback'] is False
        assert resp.data['skipped_sheets'] == []
        from apps.categories.models import Category
        assert Category.objects.get(asset_code='A-a00002').management_type == 'quantity'
        assert Category.objects.get(asset_code='A-a00001').management_type == 'instance'
        assert Category.objects.get(asset_code='B-b00001').management_type == 'consumable'
        by_name = {s['name']: s for s in resp.data['sheets']}
        assert by_name['消耗品']['management_type'] == 'consumable'
        assert by_name['消耗品']['imported'] == 1

    def test_unmatched_sheet_listed_in_skipped(self, admin_client):
        buf = _make_xlsx_multi({
            '消耗品': [['低值易耗品类', '办公耗材', '笔', 'B-b00002', '支', 20, '']],
            'Sheet1': [['x', 'x', 'x', 'SKIP-001', 'x', '', '']],
        })
        resp = _upload_url(admin_client, '/api/categories/import', buf)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 1
        assert resp.data['skipped_sheets'] == ['Sheet1']
        from apps.categories.models import Category
        assert not Category.objects.filter(asset_code='SKIP-001').exists()

    def test_no_matched_sheet_falls_back_to_active(self, admin_client):
        rows = [['办公类', '电子设备', '投影仪', 'CAT-F001', '台', '', '']]
        buf = _make_xlsx(CATEGORY_TEMPLATE_HEADERS, rows)  # 默认 sheet 名 "Sheet"
        resp = _upload_url(admin_client, '/api/categories/import', buf)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 1
        assert resp.data['fallback'] is True
        from apps.categories.models import Category
        assert Category.objects.get(asset_code='CAT-F001').management_type == 'quantity'

    def test_stock_guard_blocks_management_change(self, admin_client, branch, make_stock):
        """已有台账存量的品目，导入改管理方式必须被跳过。"""
        from apps.assets.services import ledger
        stock = make_stock('GUA-001', qty=5, column=ledger.COLUMN_IN_USE)
        target = stock.item
        buf = _make_xlsx_multi({
            '消耗品': [['低值易耗品类', '办公耗材', target.asset_name, target.asset_code, '支', '', '']],
        })
        resp = _upload_url(admin_client, '/api/categories/import', buf)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 0
        assert '存量' in resp.data['errors'][0]
        target.refresh_from_db()
        assert target.management_type == 'quantity'

    def test_no_stock_change_allowed(self, admin_client, test_category):
        """无存量的品目，导入可改管理方式。"""
        buf = _make_xlsx_multi({
            '实例管理': [['固定资产类', '办公设备', test_category.asset_name, test_category.asset_code, '台', '', '']],
        })
        resp = _upload_url(admin_client, '/api/categories/import', buf)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 1
        test_category.refresh_from_db()
        assert test_category.management_type == 'instance'


class TestCategoryExport:
    def test_export_with_data(self, admin_client, test_category):
        resp = admin_client.get('/api/categories/export')
        headers, rows = _parse_excel_response(resp)
        assert len(rows) >= 1


# ===========================================================================
# 5-8. Transfer module (purchase/assign/transfer/recovery)
# ===========================================================================

# Template headers must match the TYPE_TEMPLATES in TransferViewSet exactly
# P2 明细行化后断言分三层：check_fields=单头字段；line_check_fields=明细行字段；
# item_check_fields=字典联查回显字段（单位/类目等行内不存，取自品目字典）。
TRANSFER_TYPE_TEMPLATES = {
    'purchase': {
        'template_headers': ['采购日期', '分公司', '资产编号', '规格型号',
                             '供应商', '采购数量', '单价', '需求部门', '备注'],
        'sample_row': ['2026-03-01', '测试分公司', 'PUR-001', '规格X',
                       '供应商A', 10, 50.0, '研发部', '采购备注'],
        'check_fields': {'需求部门': '研发部'},
        'line_supplier': '供应商A',
        'line_check_fields': {'单价': 50.0},
        'item_check_fields': {},
    },
    'assign': {
        # 领用行使用人/部门必填（修订 2.2）：导入模板加"使用人"列，领用部门解析行级外键
        'template_headers': ['分公司', '日期', '资产编号', '领用数量', '使用人', '领用部门', '用途', '备注'],
        'sample_row': ['测试分公司', '2026-03-01', 'AST-TEST-001', 5, '张三', '行政部', '办公用', ''],
        'check_fields': {'用途': '办公用'},
        'line_check_fields': {'数量': 5, '使用人': '张三'},
        'item_check_fields': {},
    },
    'transfer': {
        'template_headers': ['调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
                             '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
                             '调出负责人', '调入负责人', '备注'],
        'sample_row': ['2026-03-01', '上海分公司', '行政部', '杭州分公司', '研发部',
                       'TRF-001', '调拨物品C', '规格Y', 3, '部门调整', '王五', '赵六', ''],
        'check_fields': {'调出分公司': '上海分公司'},
        'line_check_fields': {'数量': 3},
        'item_check_fields': {},
    },
    'recovery': {
        # Must match TYPE_TEMPLATES['recovery']['headers'] in views.py exactly
        'template_headers': ['分公司', '资产编号', '资产类目', '物品分类', '资产名称', '回收分类',
                             '入库日期', '数量', '单位', '规格', '出库日期', '所属部门',
                             '存放位置', '经办人', '备注'],
        # Must match import parsing: row[0]=分公司, row[1]=资产编号, row[2]=资产类目,
        # row[3]=物品分类, row[4]=资产名称, row[5]=回收分类, row[6]=入库日期(→调拨日期),
        # row[7]=数量, row[8]=单位, row[9]=规格, row[10]=出库日期, row[11]=所属部门,
        # row[12]=?(unused), row[13]=存放位置, row[14]=经办人(→采购经办人), row[15]=备注
        'sample_row': ['测试分公司', 'REC-001', '电子设备', '电脑', '回收电脑',
                       '闲置回收', '2026-03-01', 2, '台', '型号Z', '2026-03-05',
                       '行政部', '仓库B', '张采购', '回收备注'],
        'check_fields': {'回收分类': '闲置回收', '采购经办人': '张采购'},
        'line_check_fields': {'存放位置': '仓库B'},
        'item_check_fields': {'unit': '台', 'asset_category': '电子设备', 'item_category': '电脑'},
    },
}


class TestTransferTemplates:
    @pytest.mark.parametrize('ttype', ['purchase', 'assign', 'transfer', 'recovery'])
    def test_download_template(self, admin_client, ttype):
        tpl = TRANSFER_TYPE_TEMPLATES[ttype]
        resp = admin_client.get(f'/api/transfers/template?type={ttype}')
        headers, rows = _parse_excel_response(resp)
        assert rows == []
        for h in tpl['template_headers']:
            assert h in headers, f"[{ttype}] Missing header: {h}"


def _seed_recovery_dictionary(test_branch=None):
    """预置 REC-001 字典展示值（单位/类目），与导入模板样例行一致——P2 起这些值取自字典而非行内。

    回收导入受在用软预检（第 7 案修复）：样例行 数量2 需有台账在用底数。
    """
    from apps.categories.models import Category
    Category.objects.filter(asset_code='REC-001').update(
        asset_category='电子设备', item_category='电脑', unit='台',
    )
    if test_branch is not None:
        from apps.assets.services import ledger
        item = Category.objects.filter(asset_code='REC-001').first()
        if item is not None:
            ledger.apply_adjustment(test_branch, item, ledger.COLUMN_IN_USE, 5, '导入测试造数')


class TestTransferImport:
    @pytest.mark.parametrize('ttype', ['purchase', 'assign', 'transfer', 'recovery'])
    def test_import_valid_data(self, admin_client, ttype, test_branch):
        from apps.transfers.models import Transfer
        from apps.organizations.models import Branch, Department
        # transfer 类型引用 上海/杭州分公司，确保其存在于组织架构（导入现校验分公司存在性）
        Branch.objects.create(name='上海分公司', code='SH001', team=test_branch.team)
        Branch.objects.create(name='杭州分公司', code='HZ001', team=test_branch.team)
        if ttype == 'assign':
            # 领用部门按（分公司, 部门名）解析行级外键，样例行的"行政部"需在字典内
            Department.objects.get_or_create(branch=test_branch, name='行政部')
        if ttype == 'recovery':
            _seed_recovery_dictionary(test_branch)
        tpl = TRANSFER_TYPE_TEMPLATES[ttype]
        buf = _make_xlsx(tpl['template_headers'], [tpl['sample_row']])
        resp = _upload_url(admin_client, '/api/transfers/import', buf, params=f'type={ttype}')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] >= 1
        t = Transfer.objects.filter(action_type=ttype).last()
        assert t is not None, f"No transfer found for type {ttype}"
        for field, expected in tpl['check_fields'].items():
            actual = getattr(t, field)
            if isinstance(expected, (int, float)):
                assert float(actual) == float(expected), f"[{ttype}] {field}: {actual} != {expected}"
            else:
                assert actual == expected, f"[{ttype}] {field}: '{actual}' != '{expected}'"
        line = t.lines.select_related('item').first()
        if tpl.get('line_supplier'):
            assert line.供应商 == tpl['line_supplier'], f"[{ttype}] line supplier mismatch: '{line.供应商}'"
        assert line is not None, f"[{ttype}] No transfer line found"
        for field, expected in tpl['line_check_fields'].items():
            actual = getattr(line, field)
            if isinstance(expected, (int, float)):
                assert float(actual) == float(expected), f"[{ttype}] line {field}: {actual} != {expected}"
            else:
                assert actual == expected, f"[{ttype}] line {field}: '{actual}' != '{expected}'"
        for field, expected in tpl['item_check_fields'].items():
            actual = getattr(line.item, field)
            assert actual == expected, f"[{ttype}] item {field}: '{actual}' != '{expected}'"

    def test_recovery_import_all_fields(self, admin_client, test_branch):
        """Verify all recovery-specific fields survive import (单头 + 明细行 + 字典联查)."""
        from apps.transfers.models import Transfer
        _seed_recovery_dictionary(test_branch)
        tpl = TRANSFER_TYPE_TEMPLATES['recovery']
        buf = _make_xlsx(tpl['template_headers'], [tpl['sample_row']])
        resp = _upload_url(admin_client, '/api/transfers/import', buf, params='type=recovery')
        assert resp.status_code == status.HTTP_200_OK
        t = Transfer.objects.filter(action_type='recovery').last()
        assert t is not None
        assert t.回收分类 == '闲置回收'
        assert t.采购经办人 == '张采购'
        line = t.lines.select_related('item').first()
        assert line is not None
        assert line.存放位置 == '仓库B'
        assert line.item.unit == '台'
        assert line.item.asset_category == '电子设备'
        assert line.item.item_category == '电脑'


    def test_import_rejects_unknown_branch(self, admin_client):
        # transfer 类型：调出分公司填写不存在的名称 → 该行被拒
        tpl = TRANSFER_TYPE_TEMPLATES['transfer']
        row = list(tpl['sample_row'])
        row[1] = '不存在的分公司'  # 调出分公司
        buf = _make_xlsx(tpl['template_headers'], [row])
        resp = _upload_url(admin_client, '/api/transfers/import', buf, params='type=transfer')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 0
        assert any('不存在的分公司' in e for e in resp.data['errors'])

    def test_assign_import_requires_user_and_department(self, admin_client, test_branch):
        """领用导入行缺使用人/领用部门 → 逐行报错不建单（与表单路径同口径）。"""
        from apps.organizations.models import Department
        Department.objects.get_or_create(branch=test_branch, name='行政部')
        tpl = TRANSFER_TYPE_TEMPLATES['assign']
        row = list(tpl['sample_row'])
        row[4] = ''  # 使用人留空
        row[5] = ''  # 领用部门留空
        buf = _make_xlsx(tpl['template_headers'], [row])
        resp = _upload_url(admin_client, '/api/transfers/import', buf, params='type=assign')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 0
        assert any('使用人' in e for e in resp.data['errors'])

    def test_assign_import_department_not_found(self, admin_client, test_branch):
        """领用部门不在该分公司部门字典 → 报错点名分公司与部门。"""
        tpl = TRANSFER_TYPE_TEMPLATES['assign']
        row = list(tpl['sample_row'])
        row[5] = '不存在部'  # 领用部门
        buf = _make_xlsx(tpl['template_headers'], [row])
        resp = _upload_url(admin_client, '/api/transfers/import', buf, params='type=assign')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 0
        assert any('不存在部' in e and '测试分公司' in e for e in resp.data['errors'])

    def test_purchase_import_autofills_amount(self, admin_client, test_branch):
        """采购模板无金额列 → 落库金额 = 单价 × 数量自动计算。"""
        from apps.transfers.models import Transfer
        tpl = TRANSFER_TYPE_TEMPLATES['purchase']
        row = list(tpl['sample_row'])
        buf = _make_xlsx(tpl['template_headers'], [row])
        resp = _upload_url(admin_client, '/api/transfers/import', buf, params='type=purchase')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 1
        line = Transfer.objects.filter(action_type='purchase').last().lines.first()
        assert float(line.单价) == 50.0
        assert float(line.金额) == 500.0

    def test_import_rejects_empty_branch(self, admin_client):
        # transfer 类型：调出分公司为空 → 该行被拒
        tpl = TRANSFER_TYPE_TEMPLATES['transfer']
        row = list(tpl['sample_row'])
        row[1] = ''  # 调出分公司为空
        buf = _make_xlsx(tpl['template_headers'], [row])
        resp = _upload_url(admin_client, '/api/transfers/import', buf, params='type=transfer')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 0
        assert any('调出分公司为空' in e for e in resp.data['errors'])


class TestTransferExport:
    @pytest.mark.parametrize('ttype', ['purchase', 'assign', 'transfer', 'recovery'])
    def test_export_filters_by_type(self, admin_client, ttype):
        from apps.transfers.models import Transfer, TransferLine
        from apps.categories.models import Category
        # Create one record of each type（单头 + 一条明细行，导出按行展开）
        for tt in ['purchase', 'assign', 'transfer', 'recovery']:
            item = Category.objects.create(
                asset_category='测试类目', item_category='测试分类',
                asset_name=f'导出测试-{tt}', asset_code=f'EXP-{tt}-001', unit='个',
            )
            t = Transfer.objects.create(
                调拨日期=date(2026, 3, 1),
                action_type=tt,
            )
            TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=1)
        resp = admin_client.get(f'/api/transfers/export?type={ttype}')
        headers, rows = _parse_excel_response(resp)
        assert len(rows) >= 1


# ===========================================================================
# 9. Inventory module
# ===========================================================================

class TestInventoryImportExport:
    def test_download_template(self, admin_client, admin_user):
        from apps.inventories.models import InventoryTask
        task = InventoryTask.objects.create(
            name='导入测试盘点',
            status='in_progress',
            created_by=admin_user,
        )
        resp = admin_client.get(f'/api/inventories/{task.id}/import-template')
        assert resp.status_code == status.HTTP_200_OK
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        assert wb.active is not None

    def test_import_results(self, admin_client, admin_user, branch):
        from apps.inventories.models import InventoryTask, InventoryItem
        task = InventoryTask.objects.create(
            name='结果导入测试', status='in_progress', created_by=admin_user,
        )
        from apps.assets.models import AssetStock
        from apps.assets.services import ledger
        from apps.categories.models import Category
        item = Category.objects.create(
            asset_category='测试类目', item_category='测试分类',
            asset_name='盘点导入资产', asset_code='INV-IMP-001', unit='台',
        )
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 5, '造数')
        task.branch = branch
        task.save(update_fields=['branch'])
        stock = AssetStock.objects.get(branch=branch, item=item)
        InventoryItem.objects.create(
            task=task, stock=stock,
            expected_qty=5, actual_qty=None, result='unchecked', check_count=0,
        )
        # Inventory import expects specific columns: match the actual template
        # row[1]=资产编号, row[5]=实盘数量
        headers = ['序号', '资产编号', '资产名称', '规格', '账面数量', '实盘数量', '备注']
        rows = [[1, 'INV-IMP-001', '盘点导入资产', '', 5, 5, '盘点正常']]
        buf = _make_xlsx(headers, rows)
        resp = _upload_url(admin_client, f'/api/inventories/{task.id}/import-result', buf)
        assert resp.status_code == status.HTTP_200_OK
        item = InventoryItem.objects.get(task=task, stock=stock)
        assert item.actual_qty == 5
        assert item.result == 'matched'


# ===========================================================================
# 10. Edge cases
# ===========================================================================

class TestImportEdgeCases:
    """资产导入端点已随 Asset 退役（404）。"""

    def test_asset_import_endpoint_gone(self, admin_client):
        from io import BytesIO
        buf = BytesIO(b'not excel')
        buf.name = 'test.txt'
        resp = admin_client.post('/api/assets/import', {'file': buf}, format='multipart')
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_410_GONE)






@pytest.mark.django_db
class TestPurchaseImportBranchDirection:
    """采购导入分公司方向（第 24 案）：分公司列 = 入库方（to_branch），不再误装调出。"""

    def test_purchase_import_sets_to_branch(self, admin_client, item_id, branch):
        from apps.organizations.models import Branch
        from apps.transfers.models import Transfer
        headers = ['采购日期', '分公司', '资产编号', '规格型号',
                   '供应商', '采购数量', '单价', '需求部门', '备注']
        rows = [['2026-09-13', branch.name, 'PUR-001', '', '供应商X', 2, 10, '', '']]
        buf = _make_xlsx(headers, rows)
        resp = _upload_url(admin_client, '/api/transfers/import', buf, 'type=purchase')
        assert resp.status_code == 200, resp.data
        doc = Transfer.objects.filter(
            action_type='purchase', 调入分公司=branch.name,
        ).order_by('-created_at').first()
        assert doc is not None, '导入应建出采购单'
        assert doc.to_branch_id == branch.id, '分公司列必须落 to_branch（入库方）'
        assert doc.from_branch is None, '采购单不得占用调出方'
        assert doc.调出分公司 == ''


@pytest.mark.django_db
class TestImportMergeDocs:
    """采购/领用导入合单（第 26 案）：单头键相同的多行合并一张多明细单。"""

    def test_purchase_two_rows_one_doc(self, admin_client, test_branch):
        from apps.transfers.models import Transfer
        headers = TRANSFER_TYPE_TEMPLATES['purchase']['template_headers']
        rows = [
            ['2026-09-14', test_branch.name, 'PUR-001', '', '供应商A', 10, 50.0, '', '同批'],
            ['2026-09-14', test_branch.name, 'APR-001', '', '供应商A', 5, 20.0, '', '同批'],
        ]
        buf = _make_xlsx(headers, rows)
        resp = _upload_url(admin_client, '/api/transfers/import', buf, 'type=purchase')
        assert resp.status_code == 200
        assert resp.data['imported'] == 1 and resp.data['imported_lines'] == 2
        doc = Transfer.objects.filter(action_type='purchase').order_by('-created_at').first()
        assert doc.lines.count() == 2
        assert doc.采购经办人 == resp.data and False or doc.采购经办人  # 便于失败时查看
        assert doc.采购经办人 != ''  # 操作人自动落
        assert sorted(doc.lines.values_list('item__asset_code', flat=True)) == ['APR-001', 'PUR-001']

    def test_purchase_different_keys_two_docs(self, admin_client, test_branch):
        from apps.transfers.models import Transfer
        headers = TRANSFER_TYPE_TEMPLATES['purchase']['template_headers']
        rows = [
            ['2026-09-14', test_branch.name, 'PUR-001', '', '供应商A', 10, 50.0, '研发部', '备注1'],
            ['2026-09-14', test_branch.name, 'APR-001', '', '供应商B', 5, 20.0, '行政部', '备注2'],
        ]
        buf = _make_xlsx(headers, rows)
        resp = _upload_url(admin_client, '/api/transfers/import', buf, 'type=purchase')
        assert resp.data['imported'] == 2
        assert Transfer.objects.filter(action_type='purchase', 审批状态='待审批').count() == 2

    def test_purchase_row_error_keeps_group(self, admin_client, test_branch):
        """组内一行编号不合法 → 该行报错，同组其余行仍合并建单。"""
        from apps.transfers.models import Transfer
        headers = TRANSFER_TYPE_TEMPLATES['purchase']['template_headers']
        rows = [
            ['2026-09-14', test_branch.name, 'PUR-001', '', '供应商A', 10, 50.0, '', ''],
            ['2026-09-14', test_branch.name, 'NOT-EXIST', '', '供应商A', 5, 20.0, '', ''],
        ]
        buf = _make_xlsx(headers, rows)
        resp = _upload_url(admin_client, '/api/transfers/import', buf, 'type=purchase')
        assert resp.data['imported'] == 1 and resp.data['imported_lines'] == 1
        assert any('NOT-EXIST' in e for e in resp.data['errors'])
        doc = Transfer.objects.filter(action_type='purchase').order_by('-created_at').first()
        assert doc.lines.count() == 1 and doc.lines.first().item.asset_code == 'PUR-001'

    def test_assign_two_rows_one_doc(self, admin_client, test_branch):
        from apps.organizations.models import Department
        from apps.transfers.models import Transfer
        Department.objects.get_or_create(branch=test_branch, name='行政部')
        headers = TRANSFER_TYPE_TEMPLATES['assign']['template_headers']
        rows = [
            [test_branch.name, '2026-09-14', 'AST-TEST-001', 2, '张三', '行政部', '办公', ''],
            [test_branch.name, '2026-09-14', 'AST-TEST-001', 3, '李四', '行政部', '办公', ''],
        ]
        buf = _make_xlsx(headers, rows)
        resp = _upload_url(admin_client, '/api/transfers/import', buf, 'type=assign')
        assert resp.data['imported'] == 1 and resp.data['imported_lines'] == 2
        doc = Transfer.objects.filter(action_type='assign').order_by('-created_at').first()
        assert doc.lines.count() == 2
        assert sorted(doc.lines.values_list('使用人', flat=True)) == ['张三', '李四']


@pytest.mark.django_db
class TestImportHeaderGuard:
    """导入表头守卫 + 按名取列 + 备注不拆单（第 27 案）。"""

    def test_legacy_template_rejected(self, admin_client, test_branch):
        """旧 12 列采购模板（含 物品名称/总金额/采购经办人）→ 整体 400 零入库。"""
        from apps.transfers.models import Transfer
        legacy = ['采购日期', '分公司', '资产编号', '物品名称', '规格型号', '图片',
                  '供应商', '采购数量', '单价', '总金额', '需求部门', '采购经办人', '备注']
        row = ['2026-09-14', test_branch.name, 'PUR-001', 'x', '', '', 's', 1, 1, 1, '', '', '']
        resp = _upload_url(admin_client, '/api/transfers/import', _make_xlsx(legacy, [row]), 'type=purchase')
        assert resp.status_code == 400
        assert '重新下载' in str(resp.data['detail'])
        assert Transfer.objects.filter(action_type='purchase').count() == 0

    def test_shuffled_columns_still_parse(self, admin_client, test_branch):
        """列序打乱（集合一致）仍按名正确解析。"""
        headers = ['供应商', '备注', '采购数量', '分公司', '采购日期', '单价', '资产编号', '需求部门', '规格型号']
        row = ['供X', '备', 3, test_branch.name, '2026-09-14', 10, 'PUR-001', '', '规格S']
        resp = _upload_url(admin_client, '/api/transfers/import', _make_xlsx(headers, [row]), 'type=purchase')
        assert resp.status_code == 200 and resp.data['imported'] == 1
        from apps.transfers.models import Transfer
        doc = Transfer.objects.get(action_type='purchase')
        line = doc.lines.first()
        assert line.供应商 == '供X' and line.数量 == 3 and float(line.单价) == 10.0 and line.本批规格 == '规格S'

    def test_remark_difference_still_merges(self, admin_client, test_branch):
        """两行备注不同（其余键同）→ 仍合一张单（备注取首行）。"""
        from apps.transfers.models import Transfer
        headers = TRANSFER_TYPE_TEMPLATES['purchase']['template_headers']
        rows = [
            ['2026-09-14', test_branch.name, 'PUR-001', '', '供X', 10, 5.0, '', '备注A'],
            ['2026-09-14', test_branch.name, 'APR-001', '', '供X', 5, 2.0, '', ''],
        ]
        resp = _upload_url(admin_client, '/api/transfers/import', _make_xlsx(headers, rows), 'type=purchase')
        assert resp.data['imported'] == 1
        doc = Transfer.objects.get(action_type='purchase')
        assert doc.lines.count() == 2 and doc.备注 == '备注A'


@pytest.mark.django_db
class TestImportFingerprint:
    """文件防重传（第 30 案）：同上传者同文件 24h 内重传拒。"""

    def _upload(self, client, buf):
        return _upload_url(client, '/api/transfers/import', buf, 'type=purchase')

    def test_same_file_rejected(self, admin_client, test_branch):
        from apps.transfers.models import Transfer
        headers = TRANSFER_TYPE_TEMPLATES['purchase']['template_headers']
        buf = _make_xlsx(headers, [['2026-09-15', test_branch.name, 'PUR-001', '', 'S', 1, 10, '', '']])
        r1 = self._upload(admin_client, buf)
        assert r1.status_code == 200
        buf2 = _make_xlsx(headers, [['2026-09-15', test_branch.name, 'PUR-001', '', 'S', 1, 10, '', '']])
        r2 = self._upload(admin_client, buf2)
        assert r2.status_code == 400
        assert '请勿重复上传' in str(r2.data['detail'])
        assert Transfer.objects.filter(action_type='purchase').count() == 1

    def test_modified_file_passes(self, admin_client, test_branch):
        headers = TRANSFER_TYPE_TEMPLATES['purchase']['template_headers']
        buf = _make_xlsx(headers, [['2026-09-15', test_branch.name, 'PUR-001', '', 'S', 1, 10, '', '']])
        assert self._upload(admin_client, buf).status_code == 200
        buf_mod = _make_xlsx(headers, [['2026-09-15', test_branch.name, 'PUR-001', '', 'S', 2, 10, '', '']])
        assert self._upload(admin_client, buf_mod).status_code == 200

    def test_rejected_by_header_guard_no_fingerprint(self, admin_client, test_branch):
        """表头不符整体 400 时不落指纹（允许修正模板后重传）。"""
        from apps.transfers.models import ImportFingerprint
        legacy = ['采购日期', '分公司', '资产编号', '物品名称']
        buf = _make_xlsx(legacy, [['2026-09-15', test_branch.name, 'X', 'y']])
        assert self._upload(admin_client, buf).status_code == 400
        assert ImportFingerprint.objects.count() == 0
