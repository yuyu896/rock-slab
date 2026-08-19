"""
Tests for asset summary inventory ledger (AssetStock):
model invariants, CRUD/import/export API with scoping & permissions, seed migration.
"""
import io

import pytest
from rest_framework import status

from apps.assets.models import Asset, AssetStock
from conftest import _client_for

SUMMARY_URL = '/api/assets/summary'


def _make_stock(branch, code, qty=10, warning=None, **overrides):
    defaults = dict(
        分公司=branch.name, 分公司编号=branch.code, branch=branch,
        资产编号=code, 资产类目='固定资产', 物品分类='办公设备',
        资产名称=f'物品{code}', 规格='标准', 数量=qty, 警戒线=warning,
    )
    defaults.update(overrides)
    return AssetStock.objects.create(**defaults)


def _xlsx_bytes(headers, rows):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    buf = io.BytesIO(output.getvalue())
    buf.name = 'summary.xlsx'
    return buf


TEMPLATE_HEADERS = ['分公司', '资产编号', '资产类目', '物品分类', '资产名称', '数量', '规格', '警戒线']


# ---------------------------------------------------------------------------
# 模型：唯一约束 + 是否充足自动重算
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAssetStockModel:
    def test_unique_branch_asset_code(self, branch):
        _make_stock(branch, 'X-001')
        with pytest.raises(Exception):
            _make_stock(branch, 'X-001')

    def test_sufficient_recomputed_on_create_and_update(self, branch):
        stock = _make_stock(branch, 'X-002', qty=10, warning=5)
        assert stock.是否充足 is True

        stock.数量 = 3
        stock.save()
        stock.refresh_from_db()
        assert stock.是否充足 is False

        stock.数量 = 5
        stock.save()
        stock.refresh_from_db()
        assert stock.是否充足 is True

    def test_no_warning_line_means_sufficient(self, branch):
        stock = _make_stock(branch, 'X-003', qty=0, warning=None)
        assert stock.是否充足 is True

    def test_api_cannot_override_sufficiency(self, supervisor_user, branch):
        """客户端传入是否充足=False 被忽略，仍按数量/警戒线计算。"""
        stock = _make_stock(branch, 'X-004', qty=9, warning=5)
        client = _client_for(supervisor_user)
        resp = client.patch(f'{SUMMARY_URL}/{stock.id}', {'数量': 9, '是否充足': False})
        assert resp.status_code == 200
        stock.refresh_from_db()
        assert stock.是否充足 is True


# ---------------------------------------------------------------------------
# API：列表/筛选/数据范围/权限
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAssetStockList:
    def test_list_paginated_shape(self, authenticated_client, branch):
        _make_stock(branch, 'CS-1', qty=3)
        resp = authenticated_client.get(SUMMARY_URL)
        assert resp.status_code == 200
        assert set(resp.data.keys()) == {'count', 'next', 'previous', 'results'}
        assert resp.data['count'] == 1
        row = resp.data['results'][0]
        assert row['资产编号'] == 'CS-1'
        assert row['数量'] == 3
        assert row['是否充足'] is True

    def test_list_filters(self, authenticated_client, branch, second_branch):
        _make_stock(branch, 'CS-1')
        _make_stock(branch, 'CS-2', 资产类目='耗材')
        _make_stock(second_branch, 'RG-1')
        resp = authenticated_client.get(
            SUMMARY_URL, {'branch': branch.name, 'category': '耗材'})
        codes = [r['资产编号'] for r in resp.data['results']]
        assert codes == ['CS-2']
        resp = authenticated_client.get(SUMMARY_URL, {'keyword': 'RG'})
        assert [r['资产编号'] for r in resp.data['results']] == ['RG-1']

    def test_list_scoped_to_authorized_branches(self, supervisor_user, branch, second_branch):
        _make_stock(branch, 'CS-1')
        _make_stock(second_branch, 'RG-1')
        client = _client_for(supervisor_user)
        resp = client.get(SUMMARY_URL)
        codes = [r['资产编号'] for r in resp.data['results']]
        assert codes == ['CS-1']

    def test_list_no_grant_returns_empty(self, db, branch):
        from apps.users.models import User
        _make_stock(branch, 'CS-1')
        user = User.objects.create_user(
            phone='13911112222', name='无授权用户', password='test123456',
            role='staff', status='active', branch=branch,
        )
        client = _client_for(user)
        resp = client.get(SUMMARY_URL)
        assert resp.status_code == 200
        assert resp.data['count'] == 0

    def test_list_unauthenticated(self, api_client):
        resp = api_client.get(SUMMARY_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAssetStockWritePermissions:
    def test_create_requires_manage_assets(self, staff_user, branch):
        client = _client_for(staff_user)
        resp = client.post(SUMMARY_URL, {
            '分公司': branch.name, '资产编号': 'NEW-1', '资产名称': '新品', '数量': 5,
        })
        assert resp.status_code == 403
        assert not AssetStock.objects.filter(资产编号='NEW-1').exists()

    def test_create_with_manage_assets(self, supervisor_user, branch):
        client = _client_for(supervisor_user)
        resp = client.post(SUMMARY_URL, {
            '分公司': branch.name, '资产编号': 'NEW-1', '资产类目': '固定资产',
            '物品分类': '办公设备', '资产名称': '新品', '数量': 5, '规格': 'S', '警戒线': 2,
        })
        assert resp.status_code == 201
        stock = AssetStock.objects.get(资产编号='NEW-1')
        assert stock.分公司 == branch.name
        assert stock.分公司编号 == branch.code
        assert stock.branch_id == branch.id
        assert stock.是否充足 is True

    def test_create_duplicate_returns_400(self, supervisor_user, branch):
        _make_stock(branch, 'DUP-1')
        client = _client_for(supervisor_user)
        resp = client.post(SUMMARY_URL, {
            '分公司': branch.name, '资产编号': 'DUP-1', '资产名称': '重复', '数量': 1,
        })
        assert resp.status_code == 400

    def test_update_and_delete(self, supervisor_user, branch):
        stock = _make_stock(branch, 'UPD-1', qty=8, warning=6)
        client = _client_for(supervisor_user)
        resp = client.patch(f'{SUMMARY_URL}/{stock.id}', {'数量': 3})
        assert resp.status_code == 200
        stock.refresh_from_db()
        assert stock.数量 == 3
        assert stock.是否充足 is False

        resp = client.delete(f'{SUMMARY_URL}/{stock.id}')
        assert resp.status_code == 204
        assert not AssetStock.objects.filter(id=stock.id).exists()

    def test_batch_delete_out_of_scope_excluded(self, supervisor_user, branch, second_branch):
        mine = _make_stock(branch, 'BD-1')
        other = _make_stock(second_branch, 'BD-2')
        client = _client_for(supervisor_user)
        resp = client.post(f'{SUMMARY_URL}/batch-delete', {'ids': [str(mine.id), str(other.id)]}, format='json')
        assert resp.status_code == 200
        assert resp.data['deleted'] == 1
        assert AssetStock.objects.filter(id=other.id).exists()


# ---------------------------------------------------------------------------
# 导入 / 导出 / 模板
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAssetStockImportExport:
    def test_import_success(self, supervisor_user, branch):
        content = _xlsx_bytes(TEMPLATE_HEADERS, [
            [branch.name, 'IMP-1', '固定资产', '办公设备', '导入品一', 7, 'S', 3],
            [branch.name, 'IMP-2', '固定资产', '办公设备', '导入品二', 2, 'M', ''],
        ])
        client = _client_for(supervisor_user)
        resp = client.post(f'{SUMMARY_URL}/import', {'file': content}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 2

        s1 = AssetStock.objects.get(资产编号='IMP-1')
        assert s1.数量 == 7
        assert s1.警戒线 == 3
        assert s1.是否充足 is True
        assert s1.branch_id == branch.id

        s2 = AssetStock.objects.get(资产编号='IMP-2')
        assert s2.警戒线 is None
        assert s2.是否充足 is True

    def test_import_duplicate_rows_reported_others_imported(self, supervisor_user, branch):
        _make_stock(branch, 'IMP-DUP')
        content = _xlsx_bytes(TEMPLATE_HEADERS, [
            [branch.name, 'IMP-DUP', '固定资产', '办公设备', '已存在', 1, '', ''],
            [branch.name, 'IMP-OK', '固定资产', '办公设备', '新增', 4, '', ''],
        ])
        client = _client_for(supervisor_user)
        resp = client.post(f'{SUMMARY_URL}/import', {'file': content}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 1
        assert any('IMP-DUP' in e for e in resp.data['errors'])
        assert AssetStock.objects.filter(资产编号='IMP-OK').exists()

    def test_import_invalid_branch(self, supervisor_user):
        content = _xlsx_bytes(TEMPLATE_HEADERS, [
            ['不存在的分公司', 'IMP-9', '固定资产', '办公设备', '品', 1, '', ''],
        ])
        client = _client_for(supervisor_user)
        resp = client.post(f'{SUMMARY_URL}/import', {'file': content}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 0
        assert resp.data['errors']

    def test_import_requires_manage_assets(self, staff_user, branch):
        content = _xlsx_bytes(TEMPLATE_HEADERS, [[branch.name, 'IMP-403', '', '', '', 1, '', '']])
        client = _client_for(staff_user)
        resp = client.post(f'{SUMMARY_URL}/import', {'file': content}, format='multipart')
        assert resp.status_code == 403
        assert not AssetStock.objects.filter(资产编号='IMP-403').exists()

    def test_template_download_headers(self, supervisor_user):
        import openpyxl
        client = _client_for(supervisor_user)
        resp = client.get(f'{SUMMARY_URL}/template')
        assert resp.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        header = [c.value for c in wb.active[1]]
        assert header == TEMPLATE_HEADERS

    def test_export_columns(self, supervisor_client, branch):
        _make_stock(branch, 'EXP-1', qty=2, warning=5)
        resp = supervisor_client.get(f'{SUMMARY_URL}/export')
        assert resp.status_code == 200
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        header = [c.value for c in ws[1]]
        assert header == ['序号', '分公司', '资产编号', '资产类目', '物品分类', '资产名称', '数量', '规格', '警戒线', '是否充足']
        row = [c.value for c in ws[2]]
        assert row[0] == 1
        assert row[2] == 'EXP-1'
        assert row[9] == '否'


# ---------------------------------------------------------------------------
# 种子迁移：存量明细聚合生成台账
# ---------------------------------------------------------------------------

@pytest.mark.django_db(databases=['default'])
def test_seed_migration_aggregates_assets(transactional_db, branch):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.apps import apps

    executor = MigrationExecutor(connection)
    # 动态解析 0012 的前驱迁移名，避免硬编码
    predecessors = sorted(
        name for app, name in executor.loader.graph.nodes
        if app == 'assets' and name < '0012'
    )
    back_target = ('assets', predecessors[-1])
    executor.migrate([back_target])
    executor.loader.build_graph()

    old_state = executor.loader.project_state([back_target])
    OldAsset = old_state.apps.get_model('assets', 'Asset')
    OldAsset.objects.create(
        序号=1, 分公司=branch.name, 分公司编号=branch.code, branch_id=branch.id,
        资产编号='SEED-1', 资产类目='固定资产', 物品分类='办公设备',
        资产名称='种子物品', 规格='S', 数量=2, 警戒线=5, 当前状态='在库',
    )
    OldAsset.objects.create(
        序号=2, 分公司=branch.name, 分公司编号=branch.code, branch_id=branch.id,
        资产编号='SEED-1', 资产类目='固定资产', 物品分类='办公设备',
        资产名称='种子物品', 规格='S', 数量=3, 警戒线=2, 所属部门='行政部', 当前状态='在库',
    )
    OldAsset.objects.create(
        序号=3, 分公司=branch.name, 分公司编号=branch.code, branch_id=branch.id,
        资产编号='SEED-2', 资产名称='第二物品', 数量=4, 当前状态='在库',
    )
    # branch FK 缺失但名称可解析 → 种子按名称兜底挂 FK
    OldAsset.objects.create(
        序号=4, 分公司=branch.name, 分公司编号=branch.code, branch_id=None,
        资产编号='SEED-3', 资产名称='第三物品', 数量=2, 当前状态='在库',
    )

    executor.migrate([('assets', '0012_assetstock')])
    executor.loader.build_graph()

    Stock = apps.get_model('assets', 'AssetStock')
    seeded = Stock.objects.get(分公司=branch.name, 资产编号='SEED-1')
    assert seeded.数量 == 5
    assert seeded.警戒线 == 5
    assert seeded.资产名称 == '种子物品'
    assert seeded.是否充足 is True

    seeded2 = Stock.objects.get(分公司=branch.name, 资产编号='SEED-2')
    assert seeded2.数量 == 4
    assert seeded2.警戒线 is None

    seeded3 = Stock.objects.get(分公司=branch.name, 资产编号='SEED-3')
    assert seeded3.branch_id == branch.id

    # 回滚清理，避免影响后续测试的迁移状态
    executor.migrate([back_target])
    executor.migrate([('assets', '0012_assetstock')])
