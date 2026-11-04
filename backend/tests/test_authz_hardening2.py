"""authz-hardening-2 回归：盘点写接口挂码、流转单归属（创建人+admin）、低危杂项。"""
import datetime

import pytest

from conftest import _client_for
from apps.assets.models import FixedAsset
from apps.inventories.models import InventoryTask
from apps.transfers.models import Transfer
from apps.permissions.models import OperationGrant, ManagementScope


def _grant(user, code):
    OperationGrant.objects.get_or_create(user=user, code=code)
    return user


@pytest.fixture
def item_instance(branch):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='固定', item_category='办公',
        asset_name='ThinkPad T14', asset_code='NB-AH2', unit='台',
        management_type='instance',
    )


def _codeless_manager(branch):
    """有数据范围（任命/节点）、无任何操作码的分公司行政。"""
    from apps.users.models import User
    user = User.objects.create_user(
        phone='13700000099', name='无码行政', password='test123456',
        role='manager', status='active', branch=branch,
    )
    ManagementScope.objects.create(user=user, branch=branch)
    return user


def _doc(user, branch, code, *, status='待审批', action_type='purchase'):
    return Transfer.objects.create(
        单据编号=code, 调拨日期=datetime.date(2026, 9, 29),
        调入分公司=branch.name, to_branch=branch,
        action_type=action_type, 审批状态=status, created_by=user,
    )


@pytest.mark.django_db
class TestInventoryOperationCode:
    def test_codeless_user_cannot_create_or_start(self, branch):
        user = _codeless_manager(branch)
        client = _client_for(user)
        resp = client.post('/api/inventories/', {'name': '越权盘点', 'branch': branch.pk}, format='json')
        assert resp.status_code == 403
        task = InventoryTask.objects.create(name='存量任务', branch=branch, status='pending', created_by=user)
        resp = client.post(f'/api/inventories/{task.pk}/start')
        assert resp.status_code == 403

    def test_manager_with_code_not_blocked(self, manager_user, branch):
        _grant(manager_user, 'edit_inventory')
        _grant(manager_user, 'view_inventory')
        client = _client_for(manager_user)
        resp = client.post('/api/inventories/', {'name': '正常盘点', 'branch': branch.pk}, format='json')
        assert resp.status_code != 403

    def test_approve_gate_unchanged(self):
        from apps.inventories.views import InventoryTaskViewSet
        req = InventoryTaskViewSet.required_operations
        assert req['approve'] == 'review_inventory' and req['reject'] == 'review_inventory'
        assert req['create'] == 'edit_inventory' and req['import_result'] == 'edit_inventory'
        assert req['progress'] == 'view_inventory'
        assert req['report'] == req['export_report'] == 'view_inventory'
        assert req['download_template'] == 'edit_inventory'

    def test_progress_report_and_import_template_use_granular_permissions(
        self, manager_user, branch,
    ):
        OperationGrant.objects.filter(user=manager_user).delete()
        _grant(manager_user, 'edit_inventory')
        task = InventoryTask.objects.create(
            name='细粒度权限盘点', branch=branch, created_by=manager_user,
        )
        client = _client_for(manager_user)
        assert client.get(f'/api/inventories/{task.pk}/progress').status_code == 403
        assert client.get(f'/api/inventories/{task.pk}/report').status_code == 403
        assert client.get(f'/api/inventories/{task.pk}/import-template').status_code == 403
        _grant(manager_user, 'view_inventory')
        assert client.get(f'/api/inventories/{task.pk}/progress').status_code == 200
        assert client.get(f'/api/inventories/{task.pk}/report').status_code == 200
        assert client.get(f'/api/inventories/{task.pk}/import-template').status_code == 200

    def test_branch_manager_approval_uses_ownership_and_scope(self, branch, second_branch):
        from apps.users.models import User

        reviewer = User.objects.create_user(
            phone='13700000101', name='仅审批盘点', password='test123456',
            role='manager', status='active', branch=branch,
        )
        ManagementScope.objects.create(user=reviewer, branch=branch)
        _grant(reviewer, 'review_inventory')
        _grant(reviewer, 'view_inventory')
        own_pending = InventoryTask.objects.create(
            name='本人创建的待审批任务', branch=branch, status='pending_review', created_by=reviewer,
        )
        other_pending = InventoryTask.objects.create(
            name='他人创建的待审批任务', branch=branch, status='pending_review',
        )
        out_of_scope = InventoryTask.objects.create(
            name='范围外待审批', branch=second_branch, status='pending_review',
        )
        unrelated = InventoryTask.objects.create(
            name='本级非待审批', branch=branch, status='pending',
        )

        client = _client_for(reviewer)
        response = client.get('/api/inventories/')
        assert response.status_code == 200
        ids = {row['id'] for row in response.data['results']}
        assert ids == {str(own_pending.id), str(other_pending.id), str(unrelated.id)}
        assert client.get(f'/api/inventories/{own_pending.id}').status_code == 200
        assert client.get(f'/api/inventories/{other_pending.id}').status_code == 200
        assert client.get(f'/api/inventories/{out_of_scope.id}').status_code == 404
        assert client.post(f'/api/inventories/{own_pending.id}/approve').status_code == 200
        assert client.post(f'/api/inventories/{other_pending.id}/approve').status_code == 403


@pytest.mark.django_db
class TestTransferOwnership:
    def test_non_owner_cannot_update_or_delete_another_users_draft(self, staff_user, supervisor_user, branch):
        doc = _doc(staff_user, branch, 'OW-1', status='草稿')
        client = _client_for(supervisor_user)
        assert client.get(f'/api/transfers/{doc.pk}').status_code == 404
        resp = client.patch(f'/api/transfers/{doc.pk}', {}, format='json')
        assert resp.status_code == 404
        resp = client.delete(f'/api/transfers/{doc.pk}')
        assert resp.status_code == 404
        assert Transfer.objects.filter(pk=doc.pk).exists()

    def test_owner_can_resubmit(self, staff_user, branch):
        _grant(staff_user, 'edit_purchase')
        _grant(staff_user, 'view_purchase')
        _grant(staff_user, 'view_categories')
        doc = _doc(staff_user, branch, 'OW-2', status='已驳回')
        client = _client_for(staff_user)
        resp = client.post(f'/api/transfers/{doc.pk}/resubmit')
        assert resp.status_code == 200
        doc.refresh_from_db()
        assert doc.审批状态 == '待审批'

    def test_admin_cannot_view_or_operate_on_another_users_draft(self, admin_user, staff_user, branch):
        doc = _doc(staff_user, branch, 'OW-3', status='草稿')
        client = _client_for(admin_user)
        assert client.get(f'/api/transfers/{doc.pk}').status_code == 404
        assert client.post(f'/api/transfers/{doc.pk}/submit').status_code == 404
        assert client.patch(f'/api/transfers/{doc.pk}', {}, format='json').status_code == 404
        resp = client.delete(f'/api/transfers/{doc.pk}')
        assert resp.status_code == 404
        assert Transfer.objects.filter(pk=doc.pk, 审批状态='草稿').exists()

    def test_approver_not_blocked_by_ownership(self, leader_user, staff_user, branch):
        _grant(leader_user, 'approve_purchase')
        _grant(leader_user, 'view_purchase')
        doc = _doc(staff_user, branch, 'OW-4', status='待审批')
        client = _client_for(leader_user)
        resp = client.post(f'/api/transfers/{doc.pk}/approve',
                           {'approved': False, 'reason': '测试驳回'}, format='json')
        assert '仅创建人' not in str(resp.data)


@pytest.mark.django_db
class TestMiscHardening:
    def test_reassign_branch_out_of_scope_rejected(self, staff_user, supervisor_user, branch, second_branch):
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/users/{staff_user.pk}', {'branch': second_branch.pk}, format='json')
        assert resp.status_code == 400 and '授权范围' in str(resp.data)
        resp = client.patch(f'/api/users/{staff_user.pk}', {'branch': branch.pk}, format='json')
        assert resp.status_code == 200

    def test_orphan_instance_rejected_in_batch_update(self, admin_user, item_instance):
        orphan = FixedAsset.objects.create(
            item=item_instance, 内部编号='ORPH-1', 当前状态='在库', branch=None,
        )
        client = _client_for(admin_user)
        resp = client.post('/api/assets/fixed-assets/batch-update', {
            'ids': [str(orphan.pk)], '备注': 'x',
        }, format='json')
        assert resp.status_code == 200 and resp.data['updated'] == 0
        assert resp.data['errors'] == [f'{orphan.pk}: 未归属分公司']
        orphan.refresh_from_db()
        assert (orphan.备注 or '') == ''
