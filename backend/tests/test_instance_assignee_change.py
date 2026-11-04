"""Direct in-use assignee handoff and append-only instance timeline events."""
import pytest

from conftest import _client_for


def _grant(user, code):
    from apps.permissions.models import OperationGrant
    OperationGrant.objects.get_or_create(user=user, code=code)
    return user


def _instance(branch, department, no, state='在用', assignee='原使用人'):
    from apps.assets.models import FixedAsset
    from apps.categories.models import Category

    item, _ = Category.objects.get_or_create(
        asset_code='HANDOFF-001',
        defaults={
            'asset_category': '电子设备',
            'item_category': '电脑',
            'asset_name': '办公电脑',
            'unit': '台',
            'management_type': 'instance',
        },
    )
    return FixedAsset.objects.create(
        item=item,
        内部编号=f'{branch.code}-HANDOFF-{no}',
        当前状态=state,
        使用人=assignee,
        department=department,
        branch=branch,
    )


def _payload(instance, department, assignee='外部顾问', **extra):
    return {
        '使用人': assignee,
        'department': str(department.pk),
        **extra,
    }


@pytest.mark.django_db
class TestDirectAssigneeChange:
    def test_single_instance_accepts_non_account_assignee_and_preserves_ledger(
        self, supervisor_user, branch, department,
    ):
        from apps.assets.models import AssetStock, FixedAsset, FixedAssetAssigneeChange
        from apps.organizations.models import Department
        from apps.users.models import User

        _grant(supervisor_user, 'change_instance_assignee')
        from apps.permissions.models import OperationGrant
        OperationGrant.objects.filter(user=supervisor_user).exclude(
            code='change_instance_assignee',
        ).delete()
        _grant(supervisor_user, 'view_instances')
        _grant(supervisor_user, 'view_departments')
        target_department, _ = Department.objects.get_or_create(name='技术部门')
        instance = _instance(branch, department, 1)
        stock = AssetStock.objects.create(
            branch=branch, item=instance.item, 在库数量=4, 在用数量=2, 回收库数量=1,
        )

        response = _client_for(supervisor_user).post(
            f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
            _payload(instance, target_department, 原因='岗位调整'),
            format='json',
        )

        assert response.status_code == 200, response.data
        assert response.data['changed'] is True
        assert response.data['asset']['使用人'] == '外部顾问'
        assert str(response.data['asset']['department']) == str(target_department.pk)
        limited_asset = response.json()['asset']
        assert {
            'id', '内部编号', '序列号', '当前状态', '使用人', 'department',
            'departmentName', 'branch', 'branchName', 'itemCode', 'itemName',
        } <= set(limited_asset)
        assert '单价' not in limited_asset
        instance.refresh_from_db()
        assert instance.当前状态 == '在用'
        assert instance.branch_id == branch.pk
        assert instance.使用人 == '外部顾问'
        assert instance.department_id == target_department.pk
        assert not User.objects.filter(name='外部顾问').exists()
        assert FixedAssetAssigneeChange.objects.filter(instance=instance).count() == 1
        event = FixedAssetAssigneeChange.objects.get(instance=instance)
        assert event.old_assignee == '原使用人'
        assert event.new_assignee == '外部顾问'
        assert event.old_department_name == department.name
        assert event.new_department_name == target_department.name
        assert event.operator_account == supervisor_user.phone
        assert event.operator_name == supervisor_user.name
        assert event.reason == '岗位调整'
        stock.refresh_from_db()
        assert (stock.在库数量, stock.在用数量, stock.回收库数量) == (4, 2, 1)

    def test_no_change_does_not_append_event(self, supervisor_user, branch, department):
        from apps.assets.models import FixedAssetAssigneeChange

        _grant(supervisor_user, 'change_instance_assignee')
        instance = _instance(branch, department, 3)
        response = _client_for(supervisor_user).post(
            f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
            _payload(instance, department, assignee='原使用人'),
            format='json',
        )

        assert response.status_code == 200
        assert response.data['changed'] is False
        assert response.data['asset']['使用人'] == '原使用人'
        assert not FixedAssetAssigneeChange.objects.filter(instance=instance).exists()

    def test_instance_not_in_use_is_rejected_without_writing(self, supervisor_user, branch, department):
        from apps.assets.models import FixedAssetAssigneeChange
        _grant(supervisor_user, 'change_instance_assignee')
        instance = _instance(branch, department, 4, state='在库')
        response = _client_for(supervisor_user).post(
            f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
            _payload(instance, department),
            format='json',
        )

        assert response.status_code == 400
        assert instance.内部编号 in str(response.data)
        instance.refresh_from_db()
        assert instance.使用人 == '原使用人'
        assert instance.department_id == department.pk
        assert not FixedAssetAssigneeChange.objects.filter(instance=instance).exists()

    def test_draft_or_pending_transfer_occupancy_rejects_handoff(
        self, supervisor_user, branch, department,
    ):
        from apps.assets.models import FixedAssetAssigneeChange
        from apps.transfers.models import Transfer, TransferLine, TransferLineInstance

        _grant(supervisor_user, 'change_instance_assignee')
        instance = _instance(branch, department, 6)
        transfer = Transfer.objects.create(
            action_type=Transfer.ACTION_RETURN,
            调拨日期='2026-10-01',
            to_branch=branch,
            调入分公司=branch.name,
            审批状态='草稿',
            单据编号='GH-HANDOFF-001',
        )
        line = TransferLine.objects.create(
            transfer=transfer, item=instance.item, 行号=1, 数量=1,
        )
        TransferLineInstance.objects.create(line=line, instance=instance)

        response = _client_for(supervisor_user).post(
            f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
            _payload(instance, department, assignee='新使用人'),
            format='json',
        )

        assert response.status_code == 400
        assert instance.内部编号 in str(response.data)
        instance.refresh_from_db()
        assert instance.使用人 == '原使用人'
        assert not FixedAssetAssigneeChange.objects.filter(instance=instance).exists()

    def test_missing_permission_scope_and_invalid_request_are_rejected(
        self, supervisor_user, branch, second_branch, department,
    ):
        from apps.assets.models import FixedAsset
        from apps.categories.models import Category

        other_item, _ = Category.objects.get_or_create(
            asset_code='HANDOFF-002',
            defaults={
                'asset_category': '电子设备', 'item_category': '手机',
                'asset_name': '测试手机', 'unit': '台', 'management_type': 'instance',
            },
        )
        out_of_scope = FixedAsset.objects.create(
            item=other_item, 内部编号='OUT-HANDOFF-1', 当前状态='在用',
            使用人='原使用人', department=department, branch=second_branch,
        )
        from apps.permissions.models import OperationGrant
        OperationGrant.objects.filter(user=supervisor_user).delete()
        client = _client_for(supervisor_user)
        data = _payload(out_of_scope, department)
        no_permission = client.post(
            f'/api/assets/fixed-assets/{out_of_scope.pk}/change-assignee', data, format='json',
        )
        assert no_permission.status_code == 403

        _grant(supervisor_user, 'change_instance_assignee')
        _grant(supervisor_user, 'view_instances')
        _grant(supervisor_user, 'view_departments')
        out_of_scope_response = client.post(
            f'/api/assets/fixed-assets/{out_of_scope.pk}/change-assignee', data, format='json',
        )
        assert out_of_scope_response.status_code == 404
        out_of_scope.refresh_from_db()
        assert out_of_scope.使用人 == '原使用人'

        in_scope = _instance(branch, department, 7)
        old_collection_request = client.post(
            f'/api/assets/fixed-assets/{in_scope.pk}/change-assignee',
            {**_payload(in_scope, department), 'ids': [str(in_scope.pk)]}, format='json',
        )
        assert old_collection_request.status_code == 400

        invalid_department = client.post(
            f'/api/assets/fixed-assets/{in_scope.pk}/change-assignee',
            {**_payload(in_scope, department), 'department': '00000000-0000-0000-0000-000000000000'},
            format='json',
        )
        assert invalid_department.status_code == 400

    def test_timeline_merges_handoff_and_transfer_rows(
        self, authenticated_client, admin_user, branch, department,
    ):
        from apps.assets.models import FixedAsset
        from apps.assets.services.instances import change_assignee
        from apps.categories.models import Category
        from apps.transfers.models import Transfer, TransferLine, TransferLineInstance

        item, _ = Category.objects.get_or_create(
            asset_code='HANDOFF-003',
            defaults={
                'asset_category': '电子设备', 'item_category': '电脑',
                'asset_name': '时间线电脑', 'unit': '台', 'management_type': 'instance',
            },
        )
        instance = FixedAsset.objects.create(
            item=item, 内部编号='TIMELINE-HANDOFF-1', 当前状态='在用',
            使用人='张三', department=department, branch=branch,
        )
        transfer = Transfer.objects.create(
            action_type=Transfer.ACTION_ASSIGN,
            调拨日期='2026-10-01', from_branch=branch,
            调出分公司=branch.name, 审批状态='已通过', 单据编号='LY-HANDOFF-001',
        )
        line = TransferLine.objects.create(
            transfer=transfer, item=item, 行号=1, 数量=1,
            使用人='张三', department=department,
        )
        TransferLineInstance.objects.create(line=line, instance=instance)
        change_assignee(
            instance_id=instance.pk, assignee='李四', department=department,
            operator=admin_user, reason='交接',
        )

        response = authenticated_client.get(f'/api/assets/fixed-assets/{instance.pk}/timeline')

        assert response.status_code == 200
        rows = response.data['timeline']
        assert [row['kind'] for row in rows] == ['assignee_change', 'transfer']
        assert rows[0]['旧使用人'] == '张三'
        assert rows[0]['新使用人'] == '李四'
        assert rows[0]['旧部门'] == department.name
        assert rows[0]['新部门'] == department.name
        assert rows[0]['操作人']
        assert '单据编号' not in rows[0]
        assert '审批状态' not in rows[0]


@pytest.mark.django_db
class TestAssigneePermissionReads:
    def test_change_permission_reads_only_scoped_minimal_targets(
        self, supervisor_user, branch, second_branch, department,
    ):
        from apps.assets.models import FixedAsset
        from apps.categories.models import Category
        from apps.permissions.models import OperationGrant

        in_scope = _instance(branch, department, 31)
        other_item, _ = Category.objects.get_or_create(
            asset_code='HANDOFF-SCOPE-002',
            defaults={
                'asset_category': '电子设备', 'item_category': '手机',
                'asset_name': '测试手机', 'unit': '台', 'management_type': 'instance',
            },
        )
        FixedAsset.objects.create(
            item=other_item, 内部编号='OUT-HANDOFF-31', 当前状态='在用',
            使用人='范围外使用人', department=department, branch=second_branch,
        )
        OperationGrant.objects.filter(user=supervisor_user).delete()

        client = _client_for(supervisor_user)
        denied = client.get('/api/assets/fixed-assets/assignee-targets')
        assert denied.status_code == 403

        _grant(supervisor_user, 'change_instance_assignee')
        _grant(supervisor_user, 'view_instances')
        _grant(supervisor_user, 'view_departments')
        response = client.get('/api/assets/fixed-assets/assignee-targets')

        assert response.status_code == 200, response.data
        payload = response.json()
        assert payload['count'] == 1
        assert len(payload['results']) == 1
        target = payload['results'][0]
        assert target['id'] == str(in_scope.pk)
        assert set(target) == {
            'id', '内部编号', '序列号', '当前状态', '使用人', 'department',
            'departmentName', 'branch', 'branchName', 'itemCode', 'itemName',
        }

        full_list = client.get('/api/assets/fixed-assets')
        detail = client.get(f'/api/assets/fixed-assets/{in_scope.pk}')
        timeline = client.get(f'/api/assets/fixed-assets/{in_scope.pk}/timeline')
        export = client.get('/api/assets/fixed-assets/export')
        assert full_list.status_code == 200
        assert full_list.data['count'] == 1
        assert detail.status_code == 200
        assert timeline.status_code == 200
        assert export.status_code == 200


@pytest.mark.django_db
class TestAssigneeWriteArchitecture:
    def test_assignee_and_department_writes_stay_in_instance_service(self):
        from pathlib import Path
        import re

        backend_apps = Path(__file__).resolve().parent.parent / 'apps'
        assignment = re.compile(r'\.\s*(?:使用人|department)\s*=(?!=)')
        bulk_write = re.compile(r'\.(?:update|bulk_update)\s*\([^\n]*(?:使用人|department)')
        allowed_files = {'models.py', 'serializers.py'}
        allowed_dirs = {'migrations', 'services', 'tests'}
        violations = []

        for source in backend_apps.rglob('*.py'):
            relative = source.relative_to(backend_apps)
            if 'migrations' in relative.parts or 'tests' in relative.parts:
                continue
            if relative == Path('assets/services/instances.py'):
                continue
            if relative.name in allowed_files:
                continue
            for line_number, line in enumerate(source.read_text(encoding='utf-8').splitlines(), 1):
                if assignment.search(line) or bulk_write.search(line):
                    violations.append(f'{relative}:{line_number}: {line.strip()}')

        assert not violations, '实例使用人/部门写入必须收敛于 assets/services/instances.py:\n' + '\n'.join(violations)
