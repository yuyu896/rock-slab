"""
盘点状态机并发安全测试（inventory-state-machine-concurrency）。

注：测试环境用 SQLite，其 select_for_update 为 no-op，无法真正模拟多线程并发。
本测试通过「重复 approve 的幂等性」验证 _transition 的二次状态校验机制——
并发场景下第二个请求拿到锁时状态已变更，会被 can_transition 拦截，从而不重复
调整库存（设计文档 D4 / spec R1 的核心目标）。真正的多线程并发回归需在
PostgreSQL 下补测。
"""
import pytest
from conftest import _client_for


def _build_in_review_task(admin_user, branch, asset_qty, check_qty, code):
    """建任务 → start → check → submit，返回 (task_id, asset)。"""
    from apps.assets.models import Asset
    Asset.objects.create(
        序号=1, 资产编号=code, 资产名称='并发测试资产',
        资产类目='固定', 物品分类='办公',
        分公司=branch.name, 分公司编号=branch.code,
        branch=branch, 数量=asset_qty, 当前状态='在库',
    )
    client = _client_for(admin_user)
    resp = client.post('/api/inventories/', {'name': f'并发盘点-{code}', 'branch': branch.id}, format='json')
    assert resp.status_code == 201, resp.data
    task_id = resp.data['id']
    assert client.post(f'/api/inventories/{task_id}/start').status_code == 200
    asset = Asset.objects.get(资产编号=code)
    resp_check = client.post(
        f'/api/inventories/{task_id}/check', {'assetId': str(asset.id), 'qty': check_qty}, format='json',
    )
    assert resp_check.status_code == 200, resp_check.data
    assert client.post(f'/api/inventories/{task_id}/submit').status_code == 200
    return task_id, asset


@pytest.mark.django_db
class TestInventoryApproveIdempotency:
    def test_repeat_approve_no_double_adjust(self, admin_user, branch):
        """P1 盘点为记录模式：approve 不改 Asset 数量，重复 approve 仅状态拦截。"""
        # expected=10, actual=8 → 差异仅记录
        task_id, asset = _build_in_review_task(admin_user, branch, 10, 8, 'CONC-001')
        client = _client_for(admin_user)

        resp1 = client.post(f'/api/inventories/{task_id}/approve')
        assert resp1.status_code == 200
        asset.refresh_from_db()
        assert asset.数量 == 10  # 记录模式：不直改

        resp2 = client.post(f'/api/inventories/{task_id}/approve')
        assert resp2.status_code == 400
        asset.refresh_from_db()
        assert asset.数量 == 10

    def test_invalid_state_transition_rejected(self, admin_user, branch):
        """非法状态转换被 _transition 二次校验拦截（pending→in_progress→cancelled→非法）。"""
        client = _client_for(admin_user)
        resp = client.post('/api/inventories/', {'name': '状态测试', 'branch': branch.id}, format='json')
        task_id = resp.data['id']
        # pending → in_progress（合法）
        assert client.post(f'/api/inventories/{task_id}/start').status_code == 200
        # in_progress → cancelled（合法）
        assert client.post(f'/api/inventories/{task_id}/cancel').status_code == 200
        # cancelled → cancelled（非法，can_transition 拦截）→ 400
        assert client.post(f'/api/inventories/{task_id}/cancel').status_code == 400
