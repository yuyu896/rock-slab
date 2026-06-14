"""
Tests for FixedAsset model, API, and quantity sync.
"""
import pytest
from conftest import _client_for


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


def _sync_counts(asset):
    """Manually trigger sync since on_commit doesn't fire in pytest."""
    from apps.assets.signals import _sync_asset_counts
    _sync_asset_counts(asset)


@pytest.mark.django_db
class TestFixedAssetModel:
    def test_generate_internal_code(self, parent_asset):
        from apps.assets.models import FixedAsset
        code = FixedAsset.generate_internal_code('COMP-001')
        assert code == 'COMP-001-1'

    def test_internal_code_increments(self, parent_asset):
        from apps.assets.models import FixedAsset
        FixedAsset.objects.create(
            asset=parent_asset, 内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
        )
        code = FixedAsset.generate_internal_code('COMP-001')
        assert code == 'COMP-001-2'


@pytest.mark.django_db
class TestQuantitySync:
    def test_create_instance_syncs_count(self, parent_asset, branch):
        from apps.assets.models import FixedAsset
        FixedAsset.objects.create(
            asset=parent_asset, 内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
            branch=branch,
        )
        _sync_counts(parent_asset)
        parent_asset.refresh_from_db()
        assert parent_asset.数量 == 1

    def test_delete_instance_syncs_count(self, parent_asset, branch):
        from apps.assets.models import FixedAsset
        inst = FixedAsset.objects.create(
            asset=parent_asset, 内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
            branch=branch,
        )
        FixedAsset.objects.create(
            asset=parent_asset, 内部编号='COMP-001-2',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
            branch=branch,
        )
        _sync_counts(parent_asset)
        parent_asset.refresh_from_db()
        assert parent_asset.数量 == 2

        inst.delete()
        _sync_counts(parent_asset)
        parent_asset.refresh_from_db()
        assert parent_asset.数量 == 1


@pytest.mark.django_db
class TestFixedAssetAPI:
    def test_create_instance_via_api(self, supervisor_user, parent_asset):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets', {
            'asset': parent_asset.id,
            '资产编号': 'COMP-001',
            '序列号': 'SN-AAA',
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
            asset=parent_asset, 内部编号='COMP-001-1',
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

    def test_update_instance(self, supervisor_user, parent_asset, branch):
        from apps.assets.models import FixedAsset
        inst = FixedAsset.objects.create(
            asset=parent_asset, 内部编号='COMP-001-1',
            资产编号='COMP-001', 资产名称='ThinkPad T14',
            使用人='', 当前状态='在库', branch=branch,
        )
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/assets/fixed-assets/{inst.id}', {
            '使用人': '张三',
            '当前状态': '在用',
        })
        assert resp.status_code == 200
        inst.refresh_from_db()
        assert inst.使用人 == '张三'
        assert inst.当前状态 == '在用'

    def test_delete_instance(self, supervisor_user, parent_asset, branch):
        from apps.assets.models import FixedAsset
        inst = FixedAsset.objects.create(
            asset=parent_asset, 内部编号='COMP-001-1',
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
        ws.append(['资产编号', '序列号', '供应商', '使用人', '所属部门', '当前状态', '入库日期', '备注'])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = 'test.xlsx'
        return buf

    def test_import_creates_instances(self, supervisor_user, parent_asset):
        buf = self._make_xlsx([
            ['COMP-001', 'SN-001', '联想', '张三', '技术部', '在用', '', ''],
            ['COMP-001', 'SN-002', '戴尔', '李四', '市场部', '在用', '', ''],
        ])
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets/import', {'file': buf}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 2
        assert resp.data['errors'] == []

    def test_import_invalid_asset_code(self, supervisor_user, parent_asset):
        buf = self._make_xlsx([
            ['NOT-EXIST', 'SN-001', '联想', '', '', '在库', '', ''],
        ])
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets/import', {'file': buf}, format='multipart')
        assert resp.status_code == 200
        assert resp.data['imported'] == 0
        assert any('不存在' in e for e in resp.data['errors'])
