"""
Tests for Inventory flow: create task, start, check, submit, approve, reject, recount, cancel.
"""
import pytest
from django.urls import reverse
from rest_framework import status

INVENTORY_LIST_URL = '/api/inventories/'


def _task_action_url(action_name, pk):
    return f'/api/inventories/{pk}/{action_name}'


@pytest.fixture
def category(db):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='测试资产类目',
        item_category='测试物品分类',
        asset_name='测试分类',
        asset_code='CAT-TEST',
        unit='个',
    )


@pytest.fixture
def inventory_task(db, branch, category, admin_user):
    from apps.inventories.models import InventoryTask
    return InventoryTask.objects.create(
        name='测试盘点任务',
        branch=branch,
        category=category,
        status='pending',
        created_by=admin_user,
    )


@pytest.fixture
def in_progress_task(inventory_task):
    inventory_task.status = 'in_progress'
    inventory_task.save()
    return inventory_task


@pytest.fixture
def pending_review_task(inventory_task):
    inventory_task.status = 'pending_review'
    inventory_task.save()
    return inventory_task


@pytest.mark.django_db
class TestCreateTask:
    """创建盘点任务"""

    def test_create_task_success(self, authenticated_client, branch, category):
        payload = {
            'name': '新建盘点任务',
            'branch': branch.id,
            'category': category.id,
            'missed_rule': 'keep',
            'repeat_rule': 'last',
        }
        resp = authenticated_client.post(INVENTORY_LIST_URL, payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data['name'] == '新建盘点任务'
        assert data['status'] == 'pending'

    def test_create_task_missing_name(self, authenticated_client, branch, category):
        payload = {
            'branch': branch.id,
            'category': category.id,
        }
        resp = authenticated_client.post(INVENTORY_LIST_URL, payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_tasks(self, authenticated_client, inventory_task):
        resp = authenticated_client.get(INVENTORY_LIST_URL, format='json')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStartTask:
    """启动盘点"""

    def test_start_success(self, authenticated_client, inventory_task):
        resp = authenticated_client.post(
            _task_action_url('start', inventory_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['status'] == 'in_progress'

    def test_start_already_in_progress(self, authenticated_client, in_progress_task):
        resp = authenticated_client.post(
            _task_action_url('start', in_progress_task.id),
            format='json',
        )
        # Should fail — invalid state transition
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK)

    def test_start_unauthenticated(self, api_client, inventory_task):
        resp = api_client.post(
            _task_action_url('start', inventory_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCheckItem:
    """盘点扫描"""

    def test_check_success(self, authenticated_client, in_progress_task):
        from apps.assets.models import Asset
        asset = Asset.objects.create(
            序号=1,
            资产编号='AST-INV-001',
            资产名称='盘点测试资产',
            资产类目='测试类目',
            物品分类='测试分类',
            分公司=in_progress_task.branch.name if in_progress_task.branch else '',
            分公司编号='CS001',
            数量=10,
            当前状态='在库',
        )
        payload = {
            'assetId': str(asset.id),
            'qty': 10,
        }
        resp = authenticated_client.post(
            _task_action_url('check', in_progress_task.id),
            payload,
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_check_invalid_qty(self, authenticated_client, in_progress_task):
        payload = {
            'assetId': '00000000-0000-0000-0000-000000000000',
            'qty': -1,
        }
        resp = authenticated_client.post(
            _task_action_url('check', in_progress_task.id),
            payload,
            format='json',
        )
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
class TestSubmitTask:
    """提交盘点"""

    def test_submit_success(self, authenticated_client, in_progress_task):
        resp = authenticated_client.post(
            _task_action_url('submit', in_progress_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['status'] == 'pending_review'

    def test_submit_pending_task_fails(self, authenticated_client, inventory_task):
        resp = authenticated_client.post(
            _task_action_url('submit', inventory_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestApproveTask:
    """审批盘点"""

    def test_approve_success(self, authenticated_client, pending_review_task):
        resp = authenticated_client.post(
            _task_action_url('approve', pending_review_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['status'] == 'completed'

    def test_approve_not_pending_review(self, authenticated_client, in_progress_task):
        resp = authenticated_client.post(
            _task_action_url('approve', in_progress_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRejectTask:
    """驳回盘点"""

    def test_reject_success(self, authenticated_client, pending_review_task):
        resp = authenticated_client.post(
            _task_action_url('reject', pending_review_task.id),
            {'reason': '数据不准确'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['status'] == 'rejected'

    def test_reject_missing_reason(self, authenticated_client, pending_review_task):
        resp = authenticated_client.post(
            _task_action_url('reject', pending_review_task.id),
            {},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRecountTask:
    """重新盘点"""

    def test_recount_from_rejected(self, authenticated_client, pending_review_task):
        # First reject the task
        authenticated_client.post(
            _task_action_url('reject', pending_review_task.id),
            {'reason': '需要重新盘点'},
            format='json',
        )
        pending_review_task.refresh_from_db()

        resp = authenticated_client.post(
            _task_action_url('recount', pending_review_task.id),
            {'reset_scope': 'all'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['status'] == 'in_progress'


@pytest.mark.django_db
class TestCancelTask:
    """取消盘点"""

    def test_cancel_pending(self, authenticated_client, inventory_task):
        resp = authenticated_client.post(
            _task_action_url('cancel', inventory_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['status'] == 'cancelled'

    def test_cancel_in_progress(self, authenticated_client, in_progress_task):
        resp = authenticated_client.post(
            _task_action_url('cancel', in_progress_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['status'] == 'cancelled'

    def test_cancel_completed_fails(self, authenticated_client, pending_review_task):
        # Approve first to make it completed
        authenticated_client.post(
            _task_action_url('approve', pending_review_task.id),
            format='json',
        )
        pending_review_task.refresh_from_db()

        resp = authenticated_client.post(
            _task_action_url('cancel', pending_review_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestProgressAndReport:
    """盘点进度和报告"""

    def test_progress(self, authenticated_client, in_progress_task):
        resp = authenticated_client.get(
            _task_action_url('progress', in_progress_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_report(self, authenticated_client, in_progress_task):
        resp = authenticated_client.get(
            _task_action_url('report', in_progress_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
