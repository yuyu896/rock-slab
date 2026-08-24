"""
Tests for Category CRUD, permissions, import/export, and filtering.
"""
import io

import openpyxl
import pytest
from conftest import _client_for


CATEGORY_URL = '/api/categories/'

# 引用检查已改按明细行联查（TransferLine.item），用例恢复
_DESTROY_TRANSFER_REF_BROKEN = lambda test: test


def _build_import_xlsx(rows):
    """Build an xlsx byte buffer with the given rows (list of tuples)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '分类导入模板'
    headers = ['资产类目', '物品分类', '资产名称', '资产编号', '计量单位', '警戒线', '备注']
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = 'test.xlsx'
    return buf


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCategoryCRUD:
    def test_list_returns_paginated_results(self, admin_user, category):
        client = _client_for(admin_user)
        resp = client.get(CATEGORY_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert 'count' in data
        assert 'results' in data
        assert data['count'] >= 1

    def test_create_category(self, admin_user):
        client = _client_for(admin_user)
        payload = {
            'asset_category': '电子设备',
            'item_category': '笔记本',
            'asset_name': 'MacBook Pro',
            'asset_code': 'MBP-001',
            'unit': '台',
        }
        resp = client.post(CATEGORY_URL, payload)
        assert resp.status_code == 201
        assert resp.json()['资产编号'] == 'MBP-001'

    def test_create_duplicate_asset_code_returns_400(self, admin_user, category):
        client = _client_for(admin_user)
        payload = {
            'asset_category': '电子设备',
            'item_category': '笔记本',
            'asset_name': 'Duplicate',
            'asset_code': category.asset_code,
            'unit': '台',
        }
        resp = client.post(CATEGORY_URL, payload)
        assert resp.status_code == 400

    def test_partial_update_category(self, admin_user, category):
        client = _client_for(admin_user)
        resp = client.patch(f'/api/categories/{category.id}', {'asset_name': '已修改'})
        assert resp.status_code == 200
        assert resp.json()['资产名称'] == '已修改'

    @_DESTROY_TRANSFER_REF_BROKEN
    def test_delete_category(self, admin_user, category):
        from apps.categories.models import Category
        client = _client_for(admin_user)
        resp = client.delete(f'/api/categories/{category.id}')
        assert resp.status_code == 204
        assert not Category.objects.filter(id=category.id).exists()


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCategoryPermissions:
    def test_staff_cannot_create(self, staff_user):
        client = _client_for(staff_user)
        payload = {
            'asset_category': '电子设备',
            'item_category': '笔记本',
            'asset_name': 'StaffTry',
            'asset_code': 'STF-001',
            'unit': '台',
        }
        resp = client.post(CATEGORY_URL, payload)
        assert resp.status_code == 403

    def test_leader_cannot_create(self, leader_user):
        client = _client_for(leader_user)
        payload = {
            'asset_category': '电子设备',
            'item_category': '笔记本',
            'asset_name': 'LeaderTry',
            'asset_code': 'LDR-001',
            'unit': '台',
        }
        resp = client.post(CATEGORY_URL, payload)
        assert resp.status_code == 403

    def test_supervisor_can_create(self, supervisor_user):
        client = _client_for(supervisor_user)
        payload = {
            'asset_category': '电子设备',
            'item_category': '笔记本',
            'asset_name': 'SupervisorOK',
            'asset_code': 'SUP-001',
            'unit': '台',
        }
        resp = client.post(CATEGORY_URL, payload)
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Import / Export
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCategoryTemplate:
    def test_download_template(self, admin_user):
        client = _client_for(admin_user)
        resp = client.get(f'{CATEGORY_URL}template')
        assert resp.status_code == 200
        assert 'spreadsheetml' in resp['Content-Type']

    def test_import_valid_xlsx(self, admin_user):
        from apps.categories.models import Category
        client = _client_for(admin_user)
        buf = _build_import_xlsx([
            ('固定资产', '办公设备', '笔记本A', 'IMP-001', '台', 5, '测试导入'),
            ('固定资产', '办公设备', '笔记本B', 'IMP-002', '台', None, ''),
        ])
        resp = client.post(f'{CATEGORY_URL}import', {'file': buf}, format='multipart')
        assert resp.status_code == 200
        data = resp.json()
        assert data['imported'] == 2
        assert Category.objects.filter(asset_code='IMP-001').exists()

    def test_import_missing_required_fields(self, admin_user):
        client = _client_for(admin_user)
        # Row with empty required fields (asset_name is empty)
        buf = _build_import_xlsx([
            ('固定资产', '办公设备', '', 'MISS-001', '台', None, ''),
        ])
        resp = client.post(f'{CATEGORY_URL}import', {'file': buf}, format='multipart')
        assert resp.status_code == 200
        data = resp.json()
        assert data['imported'] == 0
        assert len(data['errors']) >= 1

    def test_export_xlsx(self, admin_user, category):
        client = _client_for(admin_user)
        resp = client.get(f'{CATEGORY_URL}export')
        assert resp.status_code == 200
        assert 'spreadsheetml' in resp['Content-Type']


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCategoryFiltering:
    def test_filter_by_asset_category(self, admin_user):
        from apps.categories.models import Category
        Category.objects.create(
            asset_category='电子设备', item_category='手机',
            asset_name='iPhone', asset_code='FILT-001', unit='台',
        )
        Category.objects.create(
            asset_category='办公家具', item_category='桌椅',
            asset_name='办公桌', asset_code='FILT-002', unit='张',
        )
        client = _client_for(admin_user)
        # Use the Chinese filter parameter name accepted by the filterset
        resp = client.get(CATEGORY_URL, {'资产类目': '电子设备'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['资产编号'] == 'FILT-001'

    def test_filter_by_item_category(self, admin_user):
        from apps.categories.models import Category
        Category.objects.create(
            asset_category='电子设备', item_category='手机',
            asset_name='iPhone', asset_code='FITM-001', unit='台',
        )
        Category.objects.create(
            asset_category='电子设备', item_category='平板',
            asset_name='iPad', asset_code='FITM-002', unit='台',
        )
        client = _client_for(admin_user)
        resp = client.get(CATEGORY_URL, {'物品分类': '手机'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['资产编号'] == 'FITM-001'


# ---------------------------------------------------------------------------
# Lookup by asset_code（新增表单按编号反查名称/类目/分类）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCategoryLookup:
    def test_lookup_hit(self, admin_user, category):
        client = _client_for(admin_user)
        resp = client.get(f'{CATEGORY_URL}lookup', {'asset_code': category.asset_code})
        assert resp.status_code == 200
        data = resp.json()
        assert data['资产名称'] == category.asset_name
        assert data['资产类目'] == category.asset_category
        assert data['物品分类'] == category.item_category
        assert data['计量单位'] == category.unit

    def test_lookup_miss_returns_404(self, admin_user):
        client = _client_for(admin_user)
        resp = client.get(f'{CATEGORY_URL}lookup', {'asset_code': 'NOPE-9999'})
        assert resp.status_code == 404

    def test_lookup_missing_param_returns_400(self, admin_user):
        client = _client_for(admin_user)
        resp = client.get(f'{CATEGORY_URL}lookup')
        assert resp.status_code == 400

    def test_lookup_readable_by_staff(self, staff_user, category):
        # 反查是读操作，填表需要，所有登录用户可用
        client = _client_for(staff_user)
        resp = client.get(f'{CATEGORY_URL}lookup', {'asset_code': category.asset_code})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# P1 品目字典契约（item-dictionary 能力）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestItemDictionary:
    def _payload(self, code, **extra):
        payload = {
            'asset_category': '电子设备',
            'item_category': '笔记本',
            'asset_name': f'品目 {code}',
            'asset_code': code,
            'unit': '台',
        }
        payload.update(extra)
        return payload

    def test_create_defaults_to_quantity_management(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post(CATEGORY_URL, self._payload('DICT-Q-001'))
        assert resp.status_code == 201
        assert resp.json()['管理方式'] == 'quantity'

    def test_create_instance_management(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post(
            CATEGORY_URL,
            self._payload('DICT-I-001', management_type='instance', specification='16G/512G',
                          is_rental=True, default_supplier='联想'),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['管理方式'] == 'instance'
        assert data['规格'] == '16G/512G'
        assert data['是否租用'] is True
        assert data['默认供应商'] == '联想'

    def test_invalid_management_type_rejected(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post(CATEGORY_URL, self._payload('DICT-X-001', management_type='mixed'))
        assert resp.status_code == 400

    @_DESTROY_TRANSFER_REF_BROKEN
    @_DESTROY_TRANSFER_REF_BROKEN
    def test_destroy_blocked_by_instance_reference(self, admin_user):
        from apps.assets.models import FixedAsset
        client = _client_for(admin_user)
        resp = client.post(CATEGORY_URL, self._payload('DICT-R-001'))
        code_id = resp.json()['id']
        from apps.categories.models import Category
        FixedAsset.objects.create(
            item=Category.objects.get(id=code_id),
            内部编号='DICT-R-001-1', 当前状态='在库',
        )
        resp = client.delete(f'{CATEGORY_URL}{code_id}')
        assert resp.status_code == 400
        assert '固定资产实例' in resp.json()['detail']

    @_DESTROY_TRANSFER_REF_BROKEN
    def test_destroy_allowed_without_reference(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post(CATEGORY_URL, self._payload('DICT-F-001'))
        code_id = resp.json()['id']
        resp = client.delete(f'{CATEGORY_URL}{code_id}')
        assert resp.status_code == 204

    def test_lookup_returns_dictionary_fields(self, admin_user):
        client = _client_for(admin_user)
        client.post(
            CATEGORY_URL,
            self._payload('DICT-L-001', management_type='instance', specification='定义规格'),
        )
        resp = client.get(f'{CATEGORY_URL}lookup', {'asset_code': 'DICT-L-001'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['管理方式'] == 'instance'
        assert data['规格'] == '定义规格'
        assert '默认供应商' in data

    def test_transfer_with_unregistered_code_rejected_with_suggestion(self, admin_user, branch):
        """P2 起创建走 items[].item（品目 uuid，FK 即户籍保证）；编号字符串入口只剩批量导入，
        「未登记编号拒绝 + difflib 相近提示」契约随之由导入路径承载。"""
        from apps.categories.models import Category
        # 相近编号 AST-TEST-001/002 已由 conftest 预登记，供 difflib 提示命中
        assert Category.objects.filter(asset_code='AST-TEST-001').exists()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['采购日期', '分公司', '资产编号', '物品名称', '规格型号', '图片',
                   '供应商', '采购数量', '单价', '总金额', '需求部门', '采购经办人', '备注'])
        ws.append(['2026-08-23', branch.name, 'AST-TEST-002X', '未登记品目', '', '',
                   '', 1, None, None, '', '', ''])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = 'purchase.xlsx'

        client = _client_for(admin_user)
        resp = client.post(
            '/api/transfers/import?type=purchase', {'file': buf}, format='multipart',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['imported'] == 0
        assert any('未在品目字典登记' in e for e in data['errors'])
        assert any('是否想找' in e for e in data['errors'])
