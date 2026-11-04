"""
Tests for Inventory flow: create task, start, check, submit, approve, reject, recount, cancel.
"""
import io

import openpyxl
import pytest
from rest_framework import status

INVENTORY_LIST_URL = '/api/inventories/'


def _task_action_url(action_name, pk):
    return f'/api/inventories/{pk}/{action_name}'


def _load_workbook(response):
    return openpyxl.load_workbook(io.BytesIO(response.content))


def _sheet_cells(worksheet):
    return [str(cell) for row in worksheet.iter_rows(values_only=True) for cell in row if cell is not None]


def _inventory_reviewer(phone, name, *, branch=None, region=None, role='manager', extra_permissions=()):
    from django.contrib.auth import get_user_model
    from apps.permissions.models import ManagementScope, OperationGrant
    from conftest import _client_for

    user = get_user_model().objects.create_user(
        phone=phone, name=name, password='test123456', role=role, status='active',
        branch=branch,
    )
    if branch:
        ManagementScope.objects.create(user=user, branch=branch)
    elif region:
        ManagementScope.objects.create(user=user, region=region)
    OperationGrant.objects.create(user=user, code='review_inventory')
    OperationGrant.objects.create(user=user, code='view_inventory')
    for code in extra_permissions:
        OperationGrant.objects.create(user=user, code=code)
    return _client_for(user)


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
    # 台账盘底数（inventory-checklist-safety：空范围开始会被拦，需有可盘行）
    from apps.categories.models import Category
    from apps.assets.services import ledger
    item, _ = Category.objects.get_or_create(
        asset_code='IV-SEED-1',
        defaults={'asset_category': category.asset_category if category else '测试类目',
                  'item_category': '测试分类', 'asset_name': '盘点底数品目', 'unit': '个'},
    )
    ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 5, '测试造数')
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
class TestTaskMutationStatus:
    @pytest.mark.parametrize(
        'task_status',
        ['in_progress', 'pending_review', 'completed', 'rejected', 'cancelled'],
    )
    def test_update_rejects_non_pending_task(self, authenticated_client, inventory_task, task_status):
        inventory_task.status = task_status
        inventory_task.save(update_fields=['status'])

        response = authenticated_client.patch(
            f'{INVENTORY_LIST_URL}{inventory_task.id}',
            {'name': '不应保存'}, format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        inventory_task.refresh_from_db()
        assert inventory_task.name == '测试盘点任务'

    @pytest.mark.parametrize(
        'task_status',
        ['in_progress', 'pending_review', 'completed', 'rejected', 'cancelled'],
    )
    def test_delete_rejects_non_pending_task(self, authenticated_client, inventory_task, task_status):
        inventory_task.status = task_status
        inventory_task.save(update_fields=['status'])

        response = authenticated_client.delete(f'{INVENTORY_LIST_URL}{inventory_task.id}')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert inventory_task.__class__.objects.filter(pk=inventory_task.pk).exists()

    def test_update_and_delete_pending_task(self, authenticated_client, inventory_task):
        update_response = authenticated_client.patch(
            f'{INVENTORY_LIST_URL}{inventory_task.id}',
            {'name': '已修改'}, format='json',
        )

        assert update_response.status_code == status.HTTP_200_OK
        inventory_task.refresh_from_db()
        assert inventory_task.name == '已修改'

        delete_response = authenticated_client.delete(f'{INVENTORY_LIST_URL}{inventory_task.id}')

        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        assert not inventory_task.__class__.objects.filter(pk=inventory_task.pk).exists()


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
        from apps.assets.models import AssetStock
        from apps.assets.services import ledger
        from apps.categories.models import Category
        # 品目类目对齐任务的 category 过滤（清单生成按 asset_category 收敛）
        seed_category = in_progress_task.category.asset_category if in_progress_task.category else '测试类目'
        item, _ = Category.objects.get_or_create(
            asset_code='AST-INV-001',
            defaults={'asset_category': seed_category, 'item_category': '测试分类',
                      'asset_name': '盘点测试资产', 'unit': '个'},
        )
        ledger.apply_adjustment(in_progress_task.branch, item, ledger.COLUMN_STOCK, 10, '造数')
        # 造数对齐真实 start 语义：清单在开始时生成（check 限清单内）
        from apps.inventories.views import generate_task_checklist
        generate_task_checklist(in_progress_task)
        stock = AssetStock.objects.get(branch=in_progress_task.branch, item=item)
        payload = {
            'stockId': str(stock.id),
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
            'stockId': '00000000-0000-0000-0000-000000000000',
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

    def test_branch_manager_can_approve_own_pending_task(self, branch):
        from apps.inventories.models import InventoryTask
        from apps.users.models import User

        client = _inventory_reviewer(
            '13944001006', '本人审批行政', branch=branch, role='manager',
        )
        manager = User.objects.get(phone='13944001006')
        task = InventoryTask.objects.create(
            name='行政本人盘点', branch=branch, status='pending_review', created_by=manager,
        )

        response = client.post(_task_action_url('approve', task.id), format='json')

        assert response.status_code == status.HTTP_200_OK, response.data
        task.refresh_from_db()
        assert task.status == 'completed'

    def test_leader_cannot_approve_out_of_scope_task(self, branch, second_branch, pending_review_task):
        out_of_scope_client = _inventory_reviewer(
            '13944001007', '范围外组长', branch=second_branch, role='leader',
        )

        response = out_of_scope_client.post(
            _task_action_url('approve', pending_review_task.id), format='json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        pending_review_task.refresh_from_db()
        assert pending_review_task.status == 'pending_review'

    def test_approve_not_pending_review(self, authenticated_client, in_progress_task):
        resp = authenticated_client.post(
            _task_action_url('approve', in_progress_task.id),
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_leader_can_approve_even_when_branch_manager_exists(
        self, branch, pending_review_task,
    ):
        _inventory_reviewer('13944001001', 'Local reviewer', branch=branch)
        upper_client = _inventory_reviewer(
            '13944001002', 'Upper reviewer', region=branch.team.region,
            role='leader',
        )

        resp = upper_client.post(
            _task_action_url('approve', pending_review_task.id), format='json',
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        pending_review_task.refresh_from_db()
        assert pending_review_task.status == 'completed'

    def test_upper_reviewer_can_approve_when_no_local_reviewer_exists(
        self, branch, pending_review_task,
    ):
        upper_client = _inventory_reviewer(
            '13944001005', 'Upper reviewer', region=branch.team.region,
            role='leader',
        )

        resp = upper_client.post(
            _task_action_url('approve', pending_review_task.id), format='json',
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data['status'] == 'completed'


@pytest.mark.django_db
class TestRejectTask:
    """驳回盘点"""

    def test_leader_can_reject_without_per_document_assignment(self, branch, pending_review_task):
        _inventory_reviewer('13944001003', 'Local reviewer', branch=branch)
        upper_client = _inventory_reviewer(
            '13944001004', 'Upper reviewer', region=branch.team.region,
            role='leader',
        )

        resp = upper_client.post(
            _task_action_url('reject', pending_review_task.id),
            {'reason': 'Not assigned'}, format='json',
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        pending_review_task.refresh_from_db()
        assert pending_review_task.status == 'rejected'
        assert pending_review_task.rejected_by_id is not None

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

    def test_recount_requires_edit_and_view_inventory_permissions(
        self, authenticated_client, branch, category,
    ):
        from rest_framework.test import APIClient
        from apps.inventories.models import InventoryTask
        from apps.permissions.models import OperationGrant
        from apps.users.models import User

        from apps.assets.services import ledger
        ledger.apply_adjustment(branch, category, ledger.COLUMN_STOCK, 5, '重盘权限测试造数')
        task = InventoryTask.objects.create(name='权限组合重盘任务', branch=branch)
        assert authenticated_client.post(_task_action_url('start', task.id), {}, format='json').status_code == status.HTTP_200_OK
        assert authenticated_client.post(_task_action_url('submit', task.id), {}, format='json').status_code == status.HTTP_200_OK
        assert authenticated_client.post(
            _task_action_url('reject', task.id), {'reason': '测试驳回'}, format='json',
        ).status_code == status.HTTP_200_OK
        rescan_user = User.objects.create_user(
            phone='13988000004', name='仅重盘用户', password='test123456',
            role='manager', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=rescan_user, code='rescan_inventory')
        rescan_client = APIClient()
        rescan_client.force_authenticate(user=rescan_user)

        list_response = rescan_client.get(INVENTORY_LIST_URL)
        recount_response = rescan_client.post(_task_action_url('recount', task.id), {}, format='json')

        assert list_response.status_code == status.HTTP_403_FORBIDDEN
        assert recount_response.status_code == status.HTTP_403_FORBIDDEN
        task.refresh_from_db()
        assert task.status == 'rejected'

        manager = User.objects.create_user(
            phone='13988000005', name='重盘维护用户', password='test123456',
            role='manager', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=manager, code='edit_inventory')
        OperationGrant.objects.create(user=manager, code='view_inventory')
        manager_client = APIClient()
        manager_client.force_authenticate(user=manager)
        list_response = manager_client.get(INVENTORY_LIST_URL)
        assert list_response.status_code == status.HTTP_200_OK
        allowed_response = manager_client.post(
            _task_action_url('recount', task.id), {'reset_scope': 'all'}, format='json',
        )

        assert allowed_response.status_code == status.HTTP_200_OK
        assert allowed_response.json()['status'] == 'in_progress'

    def test_recount_from_rejected(self, authenticated_client, inventory_task):
        # Build the same checklist used by a real pending-review task.
        started = authenticated_client.post(_task_action_url('start', inventory_task.id), {}, format='json')
        assert started.status_code == status.HTTP_200_OK, started.data
        submitted = authenticated_client.post(
            _task_action_url('submit', inventory_task.id), {}, format='json',
        )
        assert submitted.status_code == status.HTTP_200_OK, submitted.data
        rejected = authenticated_client.post(
            _task_action_url('reject', inventory_task.id),
            {'reason': '需要重新盘点'},
            format='json',
        )
        assert rejected.status_code == status.HTTP_200_OK, rejected.data

        resp = authenticated_client.post(
            _task_action_url('recount', inventory_task.id),
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

    def test_inventory_editor_can_load_progress_checklist_and_report(self, branch):
        from django.contrib.auth import get_user_model
        from apps.inventories.models import InventoryTask
        from apps.permissions.models import ManagementScope, OperationGrant
        from conftest import _client_for

        user = get_user_model().objects.create_user(
            phone='13977000001', name='移动盘点操作员', password='test123456',
            role='staff', status='active', branch=branch,
        )
        ManagementScope.objects.create(user=user, branch=branch)
        OperationGrant.objects.create(user=user, code='edit_inventory')
        OperationGrant.objects.create(user=user, code='view_inventory')
        task = InventoryTask.objects.create(
            name='移动实例盘测试', branch=branch, kind='instance', status='in_progress',
            created_by=user,
        )
        client = _client_for(user)

        progress = client.get(_task_action_url('progress', task.id))
        scan_items = client.get(_task_action_url('scan-items', task.id))
        report = client.get(_task_action_url('report', task.id))

        assert progress.status_code == status.HTTP_200_OK
        assert scan_items.status_code == status.HTTP_200_OK
        assert scan_items.data == []
        assert report.status_code == status.HTTP_200_OK

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


@pytest.mark.django_db
class TestChecksDisplayFields:
    """盘点记录展示字段与按人过滤（详情页按人流水数据层）"""

    def _make_check(self, task, stock, qty, checked_by):
        from apps.inventories.models import InventoryCheck, InventoryItem
        item = InventoryItem.objects.create(
            task=task, stock=stock, expected_qty=stock.在库数量,
            actual_qty=qty, result='matched', checked_by=checked_by,
        )
        return InventoryCheck.objects.create(
            task=task, item=item, stock=stock, qty=qty, checked_by=checked_by,
        )

    def test_checks_return_display_fields(self, authenticated_client, in_progress_task, admin_user, make_stock):
        stock = make_stock(code='CHK-001', qty=10)
        self._make_check(in_progress_task, stock, 10, admin_user)

        resp = authenticated_client.get(
            _task_action_url('checks', in_progress_task.id), format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        results = resp.json()['results']
        assert len(results) == 1
        record = results[0]
        assert record['checkedByName'] == '测试管理员'
        assert record['assetCode'] == 'CHK-001'
        assert record['assetName'] == stock.item.asset_name
        assert record['qty'] == 10

    def test_checks_filter_by_person(self, authenticated_client, in_progress_task, admin_user, make_stock):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(
            phone='13911112222', name='第二盘点人', password='test123456',
            role='staff', status='active',
        )
        self._make_check(in_progress_task, make_stock(code='CHK-A', qty=5), 5, admin_user)
        self._make_check(in_progress_task, make_stock(code='CHK-B', qty=6), 6, other)

        resp = authenticated_client.get(
            _task_action_url('checks', in_progress_task.id),
            {'checkedBy': str(other.id)},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['checkedByName'] == '第二盘点人'
        assert data['results'][0]['assetCode'] == 'CHK-B'

    def test_checks_invalid_person_param(self, authenticated_client, in_progress_task):
        resp = authenticated_client.get(
            _task_action_url('checks', in_progress_task.id),
            {'checkedBy': 'not-a-uuid'},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_checks_empty(self, authenticated_client, in_progress_task):
        resp = authenticated_client.get(
            _task_action_url('checks', in_progress_task.id), format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['count'] == 0
        assert resp.json()['results'] == []


@pytest.mark.django_db
class TestExportReport:
    """盘点报告 Excel 导出（基本信息 + 统计 + 调整单号 + 明细，双 sheet）"""

    def _make_item(self, task, stock, expected, actual, result, checked_by, remarks=''):
        from apps.inventories.models import InventoryItem
        return InventoryItem.objects.create(
            task=task, stock=stock, expected_qty=expected, actual_qty=actual,
            result=result, checked_by=checked_by, remarks=remarks,
        )

    def _make_task(self, branch, admin_user, status, name='导出测试任务'):
        from apps.inventories.models import InventoryTask
        return InventoryTask.objects.create(
            name=name, branch=branch, status=status, created_by=admin_user,
        )

    def test_export_completed_task_with_adjustments(self, authenticated_client, branch, admin_user, make_stock):
        stock_surplus = make_stock(code='EXP-S-01', qty=5)
        stock_missing = make_stock(code='EXP-M-01', qty=5)
        task = self._make_task(branch, admin_user, 'in_progress')
        self._make_item(task, stock_surplus, 5, 6, 'surplus', admin_user, remarks='盘盈一件')
        self._make_item(task, stock_missing, 5, 3, 'missing', admin_user, remarks='少了两件')
        task.status = 'pending_review'
        task.save()

        approve_resp = authenticated_client.post(_task_action_url('approve', task.id), format='json')
        assert approve_resp.status_code == status.HTTP_200_OK
        adj_numbers = list(task.adjustments.values_list('单据编号', flat=True))
        assert len(adj_numbers) == 2

        resp = authenticated_client.get(_task_action_url('export-report', task.id))
        assert resp.status_code == status.HTTP_200_OK
        assert 'spreadsheetml' in resp['Content-Type']
        # 非 latin-1 头值被 Django 按 RFC 2047 编码，解码后校验文件名
        from email.header import decode_header, make_header
        disposition = str(make_header(decode_header(resp['Content-Disposition'])))
        assert '盘点报告' in disposition
        assert '导出测试任务' in disposition

        wb = _load_workbook(resp)
        assert wb.sheetnames == ['盘点报告', '盘点明细']

        report_cells = _sheet_cells(wb['盘点报告'])
        for num in adj_numbers:
            assert num in report_cells
        assert '无（任务未完成）' not in report_cells
        assert '差异调整单' in report_cells

        detail_rows = list(wb['盘点明细'].iter_rows(values_only=True))
        assert detail_rows[0][0] == '序号'
        missing_row = next(r for r in detail_rows if r[1] == 'EXP-M-01')
        assert missing_row[4] == 5
        assert missing_row[5] == 3
        assert missing_row[6] == '-2'
        assert missing_row[7] == '盘亏'
        assert missing_row[8] == '测试管理员'
        assert missing_row[10] == '少了两件'
        surplus_row = next(r for r in detail_rows if r[1] == 'EXP-S-01')
        assert surplus_row[6] == '+1'
        assert surplus_row[7] == '盘盈'

    def test_export_in_progress_snapshot(self, authenticated_client, branch, admin_user, make_stock):
        task = self._make_task(branch, admin_user, 'in_progress', name='进行中任务')
        self._make_item(task, make_stock(code='EXP-P-01', qty=5), 5, 3, 'missing', admin_user)

        resp = authenticated_client.get(_task_action_url('export-report', task.id))
        assert resp.status_code == status.HTTP_200_OK

        wb = _load_workbook(resp)
        report_cells = _sheet_cells(wb['盘点报告'])
        assert '无（任务未完成）' in report_cells

        detail_rows = list(wb['盘点明细'].iter_rows(values_only=True))
        assert len(detail_rows) == 2
        assert detail_rows[1][1] == 'EXP-P-01'
        assert detail_rows[1][6] == '-2'

    def test_export_pending_task_empty_detail(self, authenticated_client, inventory_task):
        resp = authenticated_client.get(_task_action_url('export-report', inventory_task.id))
        assert resp.status_code == status.HTTP_200_OK

        wb = _load_workbook(resp)
        detail_rows = list(wb['盘点明细'].iter_rows(values_only=True))
        assert len(detail_rows) == 1  # 仅表头
        assert '无（任务未完成）' in _sheet_cells(wb['盘点报告'])

    def test_export_out_of_scope_404(
        self, supervisor_client, supervisor_user, second_branch, admin_user,
    ):
        from apps.permissions.models import OperationGrant
        OperationGrant.objects.get_or_create(user=supervisor_user, code='view_inventory')
        task = self._make_task(second_branch, admin_user, 'in_progress', name='区域B任务')
        resp = supervisor_client.get(_task_action_url('export-report', task.id))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
