"""资产明细（Asset）冻结只读契约测试（P1，asset-freeze-readonly 能力）。

原 CRUD/校验/编号自增等行为随冻结下线；历史数据保留可读，写操作一律 405。
"""
import pytest
from conftest import _client_for


@pytest.mark.django_db
class TestAssetFrozenContract:
    def test_list_readable_with_history(self, authenticated_client, make_asset):
        make_asset()
        resp = authenticated_client.get('/api/assets/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 1

    def test_update_frozen_for_all_roles(
        self, supervisor_user, leader_user, staff_user, make_asset,
    ):
        asset = make_asset()
        for user in (supervisor_user, leader_user, staff_user):
            client = _client_for(user)
            resp = client.patch(f'/api/assets/{asset.id}', {'资产名称': '改'})
            assert resp.status_code == 405

    def test_delete_frozen(self, supervisor_user, make_asset):
        asset = make_asset()
        client = _client_for(supervisor_user)
        resp = client.delete(f'/api/assets/{asset.id}')
        assert resp.status_code == 405

    def test_create_frozen(self, supervisor_user, branch, category):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/', {
            '分公司': branch.name, '资产编号': category.asset_code,
            '资产类目': '固定', '物品分类': '办公', '资产名称': '新', '数量': 1,
        }, format='json')
        assert resp.status_code == 405

    def test_batch_delete_frozen(self, authenticated_client, make_asset):
        asset = make_asset()
        resp = authenticated_client.post(
            '/api/assets/batch-delete', {'ids': [str(asset.id)]}, format='json',
        )
        assert resp.status_code == 405

    def test_detail_readable(self, authenticated_client, make_asset):
        asset = make_asset()
        resp = authenticated_client.get(f'/api/assets/{asset.id}')
        assert resp.status_code == 200

    def test_export_still_works(self, authenticated_client, make_asset):
        make_asset()
        resp = authenticated_client.get('/api/assets/export')
        assert resp.status_code == 200
