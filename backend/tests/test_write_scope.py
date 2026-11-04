"""
写操作数据范围校验回归测试（write-authorization-scoping）。

验证：写操作需要目录声明的查看前置，并且只能作用于授权数据范围内的分公司。
"""
import pytest
from conftest import _client_for


@pytest.mark.django_db
class TestWriteScopeEnforcement:
    def test_transfer_create_out_of_scope_rejected(self, staff_user, second_branch, item_id):
        # staff_user 授权范围 = fixture branch，对第二分公司发起调拨应被拒
        _grant_operation(staff_user, 'edit_transfer')
        client = _client_for(staff_user)
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '调出分公司': second_branch.name,
            '调入分公司': second_branch.name,
            'items': [{'item': item_id('SCOPE-OUT-001'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 400

    def test_transfer_create_in_scope_allowed(self, staff_user, branch, item_id):
        # staff_user 对自己授权分公司发起调拨应通过 scope 校验
        _grant_operation(staff_user, 'edit_transfer')
        client = _client_for(staff_user)
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '调出分公司': branch.name,
            '调入分公司': branch.name,
            'items': [{'item': item_id('SCOPE-IN-001'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201

    def test_inventory_create_out_of_scope_rejected(self, staff_user, second_branch):
        _grant_operation(staff_user, 'edit_inventory')
        client = _client_for(staff_user)
        resp = client.post('/api/inventories/', {
            'name': '越权盘点',
            'branch': second_branch.id,
        }, format='json')
        assert resp.status_code == 400

    def test_check_asset_out_of_branch_rejected(
        self, staff_user, admin_user, branch, second_branch,
    ):
        """盘点 check 提交不属于任务分公司的资产 → 404（IDOR 修复）。"""
        _grant_operation(staff_user, 'edit_inventory')
        from apps.assets.models import AssetStock
        from apps.assets.services import ledger
        from apps.categories.models import Category
        item, _ = Category.objects.get_or_create(
            asset_code='CROSS-CHECK-001',
            defaults={'asset_category': '固定', 'item_category': '办公',
                      'asset_name': '跨范围资产', 'unit': '件'},
        )
        ledger.apply_adjustment(second_branch, item, ledger.COLUMN_STOCK, 5, '造数')
        stock = AssetStock.objects.get(branch=second_branch, item=item)
        # 任务分公司台账底数（inventory-checklist-safety：空范围开始会被拦）
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 3, '造数')
        client_admin = _client_for(admin_user)
        resp = client_admin.post('/api/inventories/', {'name': '跨范围盘点', 'branch': branch.id})
        assert resp.status_code == 201
        task_id = resp.data['id']
        assert client_admin.post(f'/api/inventories/{task_id}/start').status_code == 200

        client_staff = _client_for(staff_user)
        resp = client_staff.post(f'/api/inventories/{task_id}/check', {
            'stockId': str(stock.id), 'qty': 1,
        }, format='json')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestWritePermissionBaseline:
    """关键写 action 权限声明基线（防回归）。"""

    def test_transfer_sensitive_actions_declared(self):
        from apps.transfers.views import TransferViewSet
        from apps.transfers.authorization import transfer_permission_code
        required = TransferViewSet.required_operations
        assert required['purchase'] == ('edit_purchase', 'view_purchase', 'view_categories')
        assert required['transfer'] == ('edit_transfer', 'view_transfer', 'view_asset_ledger')
        assert transfer_permission_code('purchase', 'approve') == 'approve_purchase'
        assert transfer_permission_code('transfer', 'approve') == 'approve_internal_transfer'
        assert transfer_permission_code('transfer', 'import') == 'edit_transfer'
        assert 'warehouse' not in required

    def test_assets_write_endpoints_frozen(self):
        """P1 起 Asset 写接口整体下线（405），无需再声明编辑操作码。"""
        from importlib import import_module
        views = import_module('apps.assets.views')
        assert not hasattr(views, 'AssetViewSet')

@pytest.mark.django_db
class TestUserDirectoryScoping:
    """用户名单只读放开：list/retrieve 全量（组织架构通讯录）。

    原 write-authorization-scoping R4 的 list/retrieve 隔离已按产品决策推翻；
    写路径隔离（scope 外 get_object 404 + manage_users 权限层）不变，
    见 test_users.py TestReadOnlyDirectory / TestScopeValidation。
    """

    def test_non_admin_list_users_is_limited_to_data_scope(self, staff_user, staff_b):
        _grant_operation(staff_user, 'view_users')
        client = _client_for(staff_user)
        resp = client.get('/api/users/')
        assert resp.status_code == 200
        ids = {str(u['id']) for u in resp.data}
        assert ids == {str(staff_user.id)}

    def test_non_admin_cannot_retrieve_out_of_scope_user(self, staff_user, staff_b):
        _grant_operation(staff_user, 'view_users')
        client = _client_for(staff_user)
        resp = client.get(f'/api/users/{staff_b.id}')
        assert resp.status_code == 404


def _grant_operation(user, code):
    from apps.permissions.models import OperationGrant
    from apps.permissions.operations import OPERATION_PREREQUISITES
    OperationGrant.objects.get_or_create(user=user, code=code)
    for prerequisite in OPERATION_PREREQUISITES.get(code, ()):
        OperationGrant.objects.get_or_create(user=user, code=prerequisite)


def _ensure_category(code, management_type='quantity'):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '范围测试', 'item_category': '办公',
            'asset_name': f'品目 {code}', 'unit': '件',
            'management_type': management_type,
        },
    )
    return item


def _xlsx_bytes(header, rows):
    import io
    import openpyxl
    from django.core.files.uploadedfile import SimpleUploadedFile
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return SimpleUploadedFile('import.xlsx', buf.getvalue(), content_type='application/vnd.ms-excel')


@pytest.mark.django_db
class TestAdjustmentScope:
    """台账调整单创建必须校验目标分公司在授权范围（审计 P0-1）。"""

    def _payload(self, branch, code):
        return {
            'branch': str(branch.id), '资产编号': code,
            '目标列': '在库数量', '变动量': 5, '事由': '范围测试',
        }

    def test_out_of_scope_by_id_rejected(self, staff_user, second_branch):
        from apps.assets.models import LedgerAdjustment
        _grant_operation(staff_user, 'adjust_asset_ledger')
        _ensure_category('ADJ-SCOPE-001')
        resp = _client_for(staff_user).post(
            '/api/assets/adjustments', self._payload(second_branch, 'ADJ-SCOPE-001'), format='json',
        )
        assert resp.status_code == 400
        assert LedgerAdjustment.objects.count() == 0

    def test_out_of_scope_by_name_rejected(self, staff_user, second_branch):
        from apps.assets.models import LedgerAdjustment
        _grant_operation(staff_user, 'adjust_asset_ledger')
        _ensure_category('ADJ-SCOPE-002')
        payload = self._payload(second_branch, 'ADJ-SCOPE-002')
        payload.pop('branch')
        payload['分公司'] = second_branch.name
        resp = _client_for(staff_user).post('/api/assets/adjustments', payload, format='json')
        assert resp.status_code == 400
        assert LedgerAdjustment.objects.count() == 0

    def test_in_scope_allowed(self, staff_user, branch):
        _grant_operation(staff_user, 'adjust_asset_ledger')
        _ensure_category('ADJ-SCOPE-003')
        resp = _client_for(staff_user).post(
            '/api/assets/adjustments', self._payload(branch, 'ADJ-SCOPE-003'), format='json',
        )
        assert resp.status_code == 201

    def test_admin_exempt(self, admin_user, second_branch):
        _ensure_category('ADJ-SCOPE-004')
        resp = _client_for(admin_user).post(
            '/api/assets/adjustments', self._payload(second_branch, 'ADJ-SCOPE-004'), format='json',
        )
        assert resp.status_code == 201


@pytest.mark.django_db
class TestAssetImportScope:
    """台账增量导入：越权行进 errors、不泄露现值、confirm 不可入账（审计 P0-1）。"""

    def _file(self, branch, second_branch):
        return _xlsx_bytes(
            ['分公司', '资产编号', '在库数量'],
            [
                [branch.name, 'IMP-SCOPE-001', 5],
                [second_branch.name, 'IMP-SCOPE-002', 7],
            ],
        )

    def test_out_of_scope_row_rejected_without_leak(self, staff_user, branch, second_branch):
        _grant_operation(staff_user, 'import_asset_ledger')
        _ensure_category('IMP-SCOPE-001')
        _ensure_category('IMP-SCOPE-002')
        resp = _client_for(staff_user).post(
            '/api/assets/summary/import', {'file': self._file(branch, second_branch)},
            format='multipart',
        )
        assert resp.status_code == 200
        diffs = resp.data['diffs']
        assert len(diffs) == 1
        assert diffs[0]['资产编号'] == 'IMP-SCOPE-001'
        assert '不在你的授权范围' in ''.join(resp.data['errors'])

    def test_confirm_only_applies_in_scope_rows(self, staff_user, branch, second_branch):
        from apps.assets.models import AssetStock
        _grant_operation(staff_user, 'import_asset_ledger')
        _grant_operation(staff_user, 'adjust_asset_ledger')
        _ensure_category('IMP-SCOPE-001')
        _ensure_category('IMP-SCOPE-002')
        resp = _client_for(staff_user).post(
            '/api/assets/summary/import',
            {'file': self._file(branch, second_branch), 'confirm': '1'},
            format='multipart',
        )
        assert resp.status_code == 400
        assert resp.data['applied'] == 0
        assert AssetStock.objects.filter(
            branch=second_branch, item__asset_code='IMP-SCOPE-002',
        ).exists() is False
        assert AssetStock.objects.filter(
            branch=branch, item__asset_code='IMP-SCOPE-001',
        ).exists() is False


@pytest.mark.django_db
class TestTransferImportScope:
    """流转 Excel 导入：越权行拒绝建单、合法行照常（审计 P0-1）。"""

    def test_out_of_scope_row_rejected(self, staff_user, branch, second_branch):
        from datetime import date
        _grant_operation(staff_user, 'edit_transfer')
        _ensure_category('TR-IMP-001')
        _ensure_category('TR-IMP-002')
        f = _xlsx_bytes(
            ['调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
             '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
             '调入负责人', '备注'],
            [
                [date(2026, 1, 15), second_branch.name, '', branch.name, '',
                 'TR-IMP-001', '', '', 1, '', '', ''],
                [date(2026, 1, 15), branch.name, '', branch.name, '',
                 'TR-IMP-002', '', '', 1, '', '', ''],
            ],
        )
        resp = _client_for(staff_user).post(
            '/api/transfers/import?type=transfer', {'file': f}, format='multipart',
        )
        assert resp.status_code == 400
        assert resp.data['imported'] == 0
        assert '不在你的授权范围' in ''.join(resp.data['errors'])
        from apps.transfers.models import Transfer
        assert Transfer.objects.filter(
            action_type='transfer', lines__item__asset_code='TR-IMP-001',
        ).exists() is False
        assert Transfer.objects.filter(
            action_type='transfer', lines__item__asset_code='TR-IMP-002',
        ).exists() is False


@pytest.mark.django_db
class TestInventoryTaskHardening:
    """盘点任务：branch 必填、branch/status 不可经 PATCH 变更（审计 P0-2）。"""

    def test_create_without_branch_rejected(self, staff_user):
        _grant_operation(staff_user, 'edit_inventory')
        resp = _client_for(staff_user).post('/api/inventories/', {'name': '无分公司'}, format='json')
        assert resp.status_code == 400

    def test_patch_branch_and_status_ignored(self, admin_user, branch, second_branch):
        client = _client_for(admin_user)
        resp = client.post('/api/inventories/', {'name': 'PATCH 防御', 'branch': branch.id}, format='json')
        assert resp.status_code == 201
        tid = resp.data['id']
        resp = client.patch(
            f'/api/inventories/{tid}',
            {'branch': second_branch.id, 'status': 'completed'}, format='json',
        )
        assert resp.status_code == 200
        from apps.inventories.models import InventoryTask
        task = InventoryTask.objects.get(pk=tid)
        assert task.branch_id == branch.id
        assert task.status == 'pending'

    def test_create_in_scope_allowed(self, staff_user, branch):
        _grant_operation(staff_user, 'edit_inventory')
        resp = _client_for(staff_user).post(
            '/api/inventories/', {'name': '范围内盘点', 'branch': branch.id}, format='json',
        )
        assert resp.status_code == 201

@pytest.mark.django_db
class TestTransferSingleSideScope:
    """调拨权限单边化（修订 3.1）：创建/导入只校验调出方；调入方对调拨单只读。"""

    def _transfer_payload(self, from_branch, to_branch, code):
        item = _ensure_category(code)
        return {
            '调拨日期': '2026-01-15',
            '调出分公司': from_branch.name,
            '调入分公司': to_branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }

    def _create_transfer(self, client, from_branch, to_branch, code):
        return client.post(
            '/api/transfers/transfer',
            self._transfer_payload(from_branch, to_branch, code),
            format='json',
        )

    # ---- 创建：单边校验 ----

    def test_create_to_branch_out_of_scope_allowed(self, staff_user, branch, second_branch):
        """调入方越界不再阻断调拨（核心翻转：原双边 400 → 201）。"""
        _grant_operation(staff_user, 'edit_transfer')
        _ensure_category('SS-TB-001')
        resp = self._create_transfer(_client_for(staff_user), branch, second_branch, 'SS-TB-001')
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '待审批'

    def test_create_from_branch_out_of_scope_rejected(self, staff_user, branch, second_branch):
        """调出方越界仍拒（即使调入方在范围内）。"""
        _grant_operation(staff_user, 'edit_transfer')
        _ensure_category('SS-FB-001')
        resp = self._create_transfer(_client_for(staff_user), second_branch, branch, 'SS-FB-001')
        assert resp.status_code == 400

    def test_return_creation_is_retired_regardless_of_scope(self, staff_user, branch, second_branch):
        """归还创建停用，历史写授权也不能恢复该入口。"""
        _grant_operation(staff_user, 'create_return')
        _grant_operation(staff_user, 'submit_return')
        item = _ensure_category('SS-RT-001')
        resp = _client_for(staff_user).post('/api/transfers/return', {
            '调拨日期': '2026-01-15',
            '调出分公司': branch.name,
            '调入分公司': second_branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }, format='json')
        assert resp.status_code == 410

    def test_import_transfer_row_single_side(self, staff_user, branch, second_branch):
        """导入调拨行同口径：调入越界照常建单，调出越界进 errors。"""
        from datetime import date
        _grant_operation(staff_user, 'edit_transfer')
        _ensure_category('SS-IMP-001')
        _ensure_category('SS-IMP-002')
        f = _xlsx_bytes(
            ['调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
             '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
             '调入负责人', '备注'],
            [
                [date(2026, 1, 15), branch.name, '', second_branch.name, '',
                 'SS-IMP-001', '', '', 1, '', '', ''],
                [date(2026, 1, 15), second_branch.name, '', branch.name, '',
                 'SS-IMP-002', '', '', 1, '', '', ''],
            ],
        )
        resp = _client_for(staff_user).post(
            '/api/transfers/import?type=transfer', {'file': f}, format='multipart',
        )
        assert resp.status_code == 400
        assert resp.data['imported'] == 0
        assert len(resp.data['errors']) == 1
        from apps.transfers.models import Transfer
        assert Transfer.objects.filter(
            action_type='transfer', lines__item__asset_code='SS-IMP-001',
        ).exists() is False
        assert Transfer.objects.filter(
            action_type='transfer', lines__item__asset_code='SS-IMP-002',
        ).exists() is False

    # ---- 调入方只读：写动作收紧 ----

    def test_inbound_side_cannot_approve(self, supervisor_b, branch, second_branch, admin_user):
        """调入方审批人（范围=second）批 from=branch to=second 调拨 → 400 只读拦截。"""
        supervisor_b.role = 'leader'
        supervisor_b.save(update_fields=['role'])
        _grant_operation(supervisor_b, 'approve_internal_transfer')
        _ensure_category('SS-AP-001')
        resp = self._create_transfer(_client_for(admin_user), branch, second_branch, 'SS-AP-001')
        assert resp.status_code == 201
        tid = resp.data['id']

        resp = _client_for(supervisor_b).post(
            f'/api/transfers/{tid}/approve', {'approved': True}, format='json',
        )
        assert resp.status_code == 403
        from apps.transfers.models import Transfer
        assert Transfer.objects.get(pk=tid).审批状态 == '待审批'

    def test_outbound_leader_can_approve_other_users_document(
        self, supervisor_user, branch, second_branch, make_stock, admin_user,
    ):
        """行政组长可审批本人数据范围内的他人待审批单，台账两边联动。"""
        supervisor_user.role = 'leader'
        supervisor_user.save(update_fields=['role'])
        _grant_operation(supervisor_user, 'approve_internal_transfer')
        make_stock(code='SS-AP-002', qty=1)
        resp = self._create_transfer(_client_for(admin_user), branch, second_branch, 'SS-AP-002')
        assert resp.status_code == 201
        tid = resp.data['id']

        resp = _client_for(supervisor_user).post(
            f'/api/transfers/{tid}/approve', {'approved': True}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '已通过'

    def test_inbound_side_cannot_submit_or_resubmit(self, supervisor_b, branch, second_branch, admin_user):
        from apps.transfers.models import Transfer
        _grant_operation(supervisor_b, 'edit_transfer')
        _ensure_category('SS-SB-001')
        client = _client_for(admin_user)
        resp = client.post('/api/transfers/transfer', {
            **self._transfer_payload(branch, second_branch, 'SS-SB-001'), 'draft': True,
        }, format='json')
        assert resp.status_code == 201
        tid = resp.data['id']
        assert Transfer.objects.get(pk=tid).审批状态 == '草稿'
        Transfer.objects.filter(pk=tid).update(
            created_by=supervisor_b, 创建人=supervisor_b.name,
        )
        resp = _client_for(supervisor_b).post(f'/api/transfers/{tid}/submit', format='json')
        assert resp.status_code == 400

        t = Transfer.objects.get(pk=tid)
        t.审批状态 = '已驳回'
        t.save(update_fields=['审批状态'])
        resp = _client_for(supervisor_b).post(f'/api/transfers/{tid}/resubmit', format='json')
        assert resp.status_code == 400
        resp = _client_for(supervisor_b).patch(
            f'/api/transfers/{tid}', {'备注': '调入方试图编辑'}, format='json',
        )
        assert resp.status_code == 400

    # ---- canOperate 序列化字段 ----

    def test_can_operate_field(self, supervisor_b, branch, second_branch, admin_user):
        """调入方可读整张调拨单；历史归还不进入通用单据列表。"""
        from apps.transfers.models import Transfer

        _grant_operation(supervisor_b, 'view_transfer')
        _ensure_category('SS-CO-001')
        _ensure_category('SS-CO-002')
        client = _client_for(admin_user)
        inbound = self._create_transfer(client, branch, second_branch, 'SS-CO-001')
        assert inbound.status_code == 201
        outbound = self._create_transfer(client, second_branch, branch, 'SS-CO-002')
        assert outbound.status_code == 201
        ret = Transfer.objects.create(
            单据编号='SS-CO-RETURN-HISTORY', 调拨日期='2026-01-15',
            调入分公司=second_branch.name, to_branch=second_branch,
            action_type=Transfer.ACTION_RETURN, 审批状态='待审批',
            created_by=admin_user,
        )

        resp = _client_for(supervisor_b).get('/api/transfers/', format='json')
        assert resp.status_code == 200
        by_number = {row['单据编号']: row for row in resp.data['results']}
        row_inbound = by_number[inbound.data['单据编号']]
        row_outbound = by_number[outbound.data['单据编号']]
        assert row_inbound['canOperate'] is False
        assert row_outbound['canOperate'] is True
        assert ret.单据编号 not in by_number
        assert Transfer.objects.filter(pk=ret.pk).exists()
