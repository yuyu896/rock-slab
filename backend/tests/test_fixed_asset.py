"""
Tests for FixedAsset model, API, and quantity sync.
"""
import pytest
from conftest import _client_for

from apps.assets.views import FixedAssetViewSet

FA_TEMPLATE_HEADERS = FixedAssetViewSet.FA_TEMPLATE_HEADERS


@pytest.fixture
def parent_asset(branch):
    from apps.assets.models import Asset
    return Asset.objects.create(
        序号=1, 分公司=branch.name, 分公司编号=branch.code,
        资产编号='COMP-001', 资产类目='固定', 物品分类='办公',
        资产名称='ThinkPad T14', 数量=0, branch=branch,
    )


@pytest.fixture
def parent_asset_no_branch(db):
    from apps.assets.models import Asset
    return Asset.objects.create(
        序号=2, 分公司='其他', 分公司编号='OTHER',
        资产编号='COMP-002', 资产类目='固定', 物品分类='办公',
        资产名称='Dell Laptop', 数量=0,
    )


@pytest.fixture
def category_comp001(db):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='固定', item_category='办公',
        asset_name='ThinkPad T14', asset_code='COMP-001', unit='台',
    )


@pytest.mark.django_db
class TestFixedAssetModel:
    def test_generate_internal_code(self, parent_asset):
        from apps.assets.models import FixedAsset
        code = FixedAsset.generate_internal_code('COMP-001')
        assert code == 'COMP-001-1'

    def test_internal_code_increments(self, parent_asset):
        from apps.assets.models import FixedAsset
        FixedAsset.objects.create(
            内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
        )
        code = FixedAsset.generate_internal_code('COMP-001')
        assert code == 'COMP-001-2'


@pytest.mark.django_db
class TestFixedAssetAPI:
    def test_create_instance_via_api(self, supervisor_user, category_comp001):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets', {
            '资产编号': 'COMP-001',
            '资产名称': 'ThinkPad T14',
            '序列号': 'SN-AAA',
            '分公司': '测试分公司',
            '供应商': '联想',
        })
        assert resp.status_code == 201
        data = resp.data
        assert data['内部编号'] == 'COMP-001-1'
        assert data['资产名称'] == 'ThinkPad T14'
        assert data['序列号'] == 'SN-AAA'

    def test_list_instances(self, supervisor_user, parent_asset, branch):
        from apps.assets.models import FixedAsset
        FixedAsset.objects.create(
            内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
            序列号='SN-AAA', 供应商='联想', branch=branch,
        )
        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/fixed-assets')
        assert resp.status_code == 200
        assert resp.data['count'] == 1

    def test_staff_cannot_create(self, staff_user, parent_asset):
        client = _client_for(staff_user)
        resp = client.post('/api/assets/fixed-assets', {
            'asset': parent_asset.id,
            '资产编号': 'COMP-001',
        })
        assert resp.status_code == 403

    def test_create_by_asset_code_only(self, supervisor_user, category_comp001):
        """按资产编号定位品目创建实例（资产名称需显式提交）。"""
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets', {
            '资产编号': 'COMP-001',
            '资产名称': 'ThinkPad T14',
            '序列号': 'SN-CODE',
            '分公司': '测试分公司',
            '供应商': '联想',
        })
        assert resp.status_code == 201
        data = resp.data
        assert data['内部编号'] == 'COMP-001-1'
        assert data['资产名称'] == 'ThinkPad T14'

    def test_create_unknown_asset_code_rejected(self, supervisor_user, parent_asset):
        """资产编号在品目表不存在时拒绝录入，返回 400。"""
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets', {
            '资产编号': 'NOT-EXIST',
            '资产名称': 'ThinkPad T14',
            '序列号': 'SN-X',
            '分公司': '测试分公司',
        })
        assert resp.status_code == 400
        assert '资产编号' in resp.data
        assert '未在品目登记' in str(resp.data['资产编号'])

    def test_update_instance(self, supervisor_user, parent_asset, branch):
        from apps.assets.models import FixedAsset
        inst = FixedAsset.objects.create(
            内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
            使用人='', 当前状态='在库', branch=branch,
        )
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/assets/fixed-assets/{inst.id}', {
            '使用人': '张三',
            '当前状态': '在用',
            '资产名称': 'ThinkPad T14',
            '序列号': 'SN-1',
            '分公司': '测试分公司',
        })
        assert resp.status_code == 200
        inst.refresh_from_db()
        assert inst.使用人 == '张三'
        assert inst.当前状态 == '在用'

    def test_delete_instance(self, supervisor_user, parent_asset, branch):
        from apps.assets.models import FixedAsset
        inst = FixedAsset.objects.create(
            内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
            branch=branch,
        )
        client = _client_for(supervisor_user)
        resp = client.delete(f'/api/assets/fixed-assets/{inst.id}')
        assert resp.status_code == 204
        assert not FixedAsset.objects.filter(id=inst.id).exists()


@pytest.mark.django_db
class TestFixedAssetImport:
    def _make_xlsx(self, rows):
        import openpyxl
        import io
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(FA_TEMPLATE_HEADERS)
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = 'test.xlsx'
        return buf

    def test_import_creates_instances(self, supervisor_user, category_comp001, branch):
        # 行顺序与 FA_TEMPLATE_HEADERS 一致：分公司, 资产编号, 分公司编号, 电脑序列号, 供应商,
        # 物品分类, 资产名称, 入库日期, 是否租用, 数量, 规格, 单价, 购入金额, 出库日期,
        # 所属部门, 使用人, 当前状态, 备注
        buf = self._make_xlsx([
            [branch.name, 'COMP-001', branch.code, 'SN-001', '联想',
             '', '', '', '', '', '', '', '', '', '技术部', '张三', '在用', ''],
            [branch.name, 'COMP-001', branch.code, 'SN-002', '戴尔',
             '', '', '', '', '', '', '', '', '', '市场部', '李四', '在用', ''],
        ])
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets/import', {'file': buf}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 2
        assert resp.data['errors'] == []

    def test_import_invalid_asset_code(self, supervisor_user, parent_asset):
        # 资产编号 NOT-EXIST 未在品目登记，应在品类校验阶段被拒（分公司字段无影响）
        buf = self._make_xlsx([
            [parent_asset.分公司, 'NOT-EXIST', parent_asset.分公司编号, 'SN-001', '联想',
             '', '', '', '', '', '', '', '', '', '', '', '在库', ''],
        ])
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets/import', {'file': buf}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 0
        assert any('未在品目登记' in e for e in resp.data['errors'])
