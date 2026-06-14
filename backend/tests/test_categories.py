"""
Tests for Category CRUD, permissions, import/export, and filtering.
"""
import io

import openpyxl
import pytest
from conftest import _client_for


CATEGORY_URL = '/api/categories/'


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
