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

    def test_edit_permission_controls_all_writes_and_requires_view(self, branch, category):
        from apps.permissions.models import OperationGrant
        from apps.users.models import User

        user = User.objects.create_user(
            phone='13920000991', name='品目维护员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=user, code='edit_categories')
        client = _client_for(user)

        payload = {
            'asset_category': '电子设备',
            'item_category': '笔记本',
            'asset_name': '新建名称',
            'asset_code': 'EDIT-ONLY-001',
            'unit': '台',
        }
        assert client.post(CATEGORY_URL, payload, format='json').status_code == 403
        assert client.patch(
            f'{CATEGORY_URL}{category.id}', {'asset_name': '更新名称'}, format='json',
        ).status_code == 403
        assert client.delete(f'{CATEGORY_URL}{category.id}').status_code == 403

        OperationGrant.objects.create(user=user, code='view_categories')
        created = client.post(CATEGORY_URL, payload, format='json')
        assert created.status_code == 201
        assert client.patch(
            f'{CATEGORY_URL}{category.id}', {'asset_name': '更新名称'}, format='json',
        ).status_code == 200
        assert client.delete(f'{CATEGORY_URL}{category.id}').status_code == 204

    def test_legacy_create_permission_does_not_grant_writes(self, branch, category):
        from apps.permissions.models import OperationGrant
        from apps.users.models import User

        user = User.objects.create_user(
            phone='13920000992', name='旧品目权限', password='test123456',
            role='manager', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=user, code='create_categories')
        OperationGrant.objects.create(user=user, code='view_categories')
        client = _client_for(user)

        response = client.post(CATEGORY_URL, {
            'asset_category': '电子设备', 'item_category': '笔记本',
            'asset_name': '旧码不能新增', 'asset_code': 'LEGACY-CATEGORY-001', 'unit': '台',
        }, format='json')

        assert response.status_code == 403


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

    def test_import_requires_edit_and_view_categories(self, branch):
        from apps.permissions.models import OperationGrant
        from apps.users.models import User

        user = User.objects.create_user(
            phone='13920000993', name='品目导入员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=user, code='edit_categories')
        client = _client_for(user)
        buf = _build_import_xlsx([
            ('固定资产', '办公设备', '导入品目', 'EDIT-IMPORT-001', '台', None, ''),
        ])

        denied = client.post(f'{CATEGORY_URL}import', {'file': buf}, format='multipart')
        assert denied.status_code == 403

        OperationGrant.objects.create(user=user, code='view_categories')
        buf = _build_import_xlsx([
            ('固定资产', '办公设备', '导入品目', 'EDIT-IMPORT-001', '台', None, ''),
        ])
        allowed = client.post(f'{CATEGORY_URL}import', {'file': buf}, format='multipart')
        assert allowed.status_code == 200
        assert allowed.data['imported'] == 1

    def test_import_error_rejects_all_rows(self, admin_user, category):
        from apps.categories.models import Category
        client = _client_for(admin_user)
        original_name = category.asset_name
        buf = _build_import_xlsx([
            ('固定资产', '办公设备', '应回滚的更新', category.asset_code, '台', None, ''),
            ('固定资产', '办公设备', '应回滚的新建', 'ATOMIC-VALID-001', '台', None, ''),
            ('固定资产', '办公设备', '', 'MISS-001', '台', None, ''),
        ])
        resp = client.post(f'{CATEGORY_URL}import', {'file': buf}, format='multipart')
        assert resp.status_code == 400
        data = resp.json()
        assert data['imported'] == 0
        assert len(data['errors']) >= 1
        category.refresh_from_db()
        assert category.asset_name == original_name
        assert not Category.objects.filter(asset_code='ATOMIC-VALID-001').exists()

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

    def test_filter_by_management_type(self, admin_user):
        from apps.categories.models import Category
        Category.objects.create(
            asset_category='电子设备', item_category='手机',
            asset_name='iPhone', asset_code='FMT-001', unit='台',
        )
        Category.objects.create(
            asset_category='电子设备', item_category='打印机',
            asset_name='打印机', asset_code='FMT-002', unit='台',
            management_type='instance',
        )
        Category.objects.create(
            asset_category='低值易耗品类', item_category='办公耗材',
            asset_name='签字笔', asset_code='FMT-003', unit='支',
            management_type='consumable',
        )
        client = _client_for(admin_user)
        # 消耗品档命中
        resp = client.get(CATEGORY_URL, {'管理方式': 'consumable'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['资产编号'] == 'FMT-003'
        # 与资产类目组合筛选
        resp = client.get(CATEGORY_URL, {'管理方式': 'instance', '资产类目': '电子设备'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['资产编号'] == 'FMT-002'


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
        from apps.permissions.models import OperationGrant
        OperationGrant.objects.get_or_create(user=staff_user, code='view_categories')
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

    def test_transfer_import_unregistered_code_rejects_file_without_suggestions(self, admin_user, branch):
        """采购导入遇未登记品目时整份驳回，只提示行号和文件中的编号。"""
        from apps.categories.models import Category
        from apps.transfers.models import Transfer
        # AST-TEST-001 已登记，作为同文件中的有效行，验证不会部分创建单据。
        assert Category.objects.filter(asset_code='AST-TEST-001').exists()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['采购日期', '分公司', '资产编号', '规格型号',
                   '供应商', '采购数量', '单价', '需求部门', '备注'])
        ws.append(['2026-08-23', branch.name, 'AST-TEST-001', '',
                   '', 1, None, '', ''])
        ws.append(['2026-08-23', branch.name, 'AST-TEST-002X', '',
                   '', 1, None, '', ''])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = 'purchase.xlsx'

        client = _client_for(admin_user)
        resp = client.post(
            '/api/transfers/import?type=purchase', {'file': buf}, format='multipart',
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data['imported'] == 0
        assert any('未在品目字典登记' in e for e in data['errors'])
        assert any('AST-TEST-002X' in e for e in data['errors'])
        assert all('是否想找' not in e and 'AST-TEST-001' not in e for e in data['errors'])
        assert not Transfer.objects.filter(action_type='purchase').exists()


@pytest.mark.django_db
class TestManagementTypeSwitchGuard:
    """管理方式有存量时禁切换（审计 P0-4；item-dictionary 增量）。"""

    def _patch_type(self, client, cid, new_type):
        return client.patch(f'/api/categories/{cid}', {'management_type': new_type}, format='json')

    def test_nonzero_stock_blocks_switch_to_instance(self, admin_user, branch):
        from apps.assets.services import ledger
        from apps.categories.models import Category
        client = _client_for(admin_user)
        resp = client.post(CATEGORY_URL, {
            'asset_category': '切换', 'item_category': '办公',
            'asset_name': '有存量品目', 'asset_code': 'SWITCH-001', 'unit': '件',
        }, format='json')
        cid = resp.data['id']
        item = Category.objects.get(pk=cid)
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 3, '造数')

        resp = self._patch_type(client, cid, 'instance')
        assert resp.status_code == 400
        item.refresh_from_db()
        assert item.management_type == 'quantity'
        # 锁定标志随详情输出（.data 为未渲染原始键名，前端 JSON 为 managementLocked）
        detail = client.get(f'/api/categories/{cid}').data
        assert detail['management_locked'] is True

    def test_instance_archive_blocks_switch_to_quantity(self, admin_user):
        from apps.assets.models import FixedAsset
        from apps.categories.models import Category
        client = _client_for(admin_user)
        resp = client.post(CATEGORY_URL, {
            'asset_category': '切换', 'item_category': '办公',
            'asset_name': '挂实例品目', 'asset_code': 'SWITCH-002', 'unit': '件',
            'management_type': 'instance',
        }, format='json')
        cid = resp.data['id']
        FixedAsset.objects.create(item=Category.objects.get(pk=cid), 内部编号='SWITCH-002-1')

        resp = self._patch_type(client, cid, 'quantity')
        assert resp.status_code == 400
        assert Category.objects.get(pk=cid).management_type == 'instance'

    def test_clean_category_can_switch(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post(CATEGORY_URL, {
            'asset_category': '切换', 'item_category': '办公',
            'asset_name': '无存量品目', 'asset_code': 'SWITCH-003', 'unit': '件',
        }, format='json')
        cid = resp.data['id']

        resp = self._patch_type(client, cid, 'instance')
        assert resp.status_code == 200
        detail = client.get(f'/api/categories/{cid}').data
        assert detail['management_locked'] is False
        assert detail['管理方式'] == 'instance'
