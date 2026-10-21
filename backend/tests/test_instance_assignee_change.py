"""Direct in-use assignee handoff and append-only instance timeline events."""
import pytest

from conftest import _client_for


def _grant(user, code='manage_instances'):
    from apps.permissions.models import OperationGrant

    OperationGrant.objects.get_or_create(user=user, code=code)


def _instance(branch, department, number, state='在用', assignee='张三'):
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
        内部编号=f'{branch.code}-HANDOFF-{number}',
        当前状态=state,
        使用人=assignee,
        department=department,
        branch=branch,
    )


def _payload(department, assignee='外部顾问', **extra):
    return {'使用人': assignee, 'department': str(department.pk), **extra}


@pytest.mark.django_db
def test_change_assignee_keeps_free_text_and_appends_history(
    supervisor_user, branch, department,
):
    from apps.assets.models import FixedAssetAssigneeChange
    from apps.organizations.models import Department
    from apps.users.models import User

    _grant(supervisor_user)
    new_department, _ = Department.objects.get_or_create(name='技术部')
    instance = _instance(branch, department, 1)

    response = _client_for(supervisor_user).post(
        f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
        _payload(new_department, 原因='岗位调整'),
        format='json',
    )

    assert response.status_code == 200, response.data
    assert response.data['changed'] is True
    assert response.data['asset']['使用人'] == '外部顾问'
    instance.refresh_from_db()
    assert instance.当前状态 == '在用'
    assert instance.branch_id == branch.pk
    assert instance.使用人 == '外部顾问'
    assert instance.department_id == new_department.pk
    assert not User.objects.filter(name='外部顾问').exists()

    event = FixedAssetAssigneeChange.objects.get(instance=instance)
    assert (event.old_assignee, event.new_assignee) == ('张三', '外部顾问')
    assert (event.old_department_name, event.new_department_name) == (department.name, new_department.name)
    assert event.operator_account == supervisor_user.phone
    assert event.operator_name == supervisor_user.name
    assert event.reason == '岗位调整'


@pytest.mark.django_db
def test_unchanged_values_do_not_create_history(supervisor_user, branch, department):
    from apps.assets.models import FixedAssetAssigneeChange

    _grant(supervisor_user)
    instance = _instance(branch, department, 2)
    response = _client_for(supervisor_user).post(
        f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
        _payload(department, assignee='张三'),
        format='json',
    )

    assert response.status_code == 200
    assert response.data['changed'] is False
    assert not FixedAssetAssigneeChange.objects.filter(instance=instance).exists()


@pytest.mark.django_db
def test_permission_and_in_use_state_are_required(supervisor_user, branch, department):
    from apps.assets.models import FixedAssetAssigneeChange

    instance = _instance(branch, department, 3)
    client = _client_for(supervisor_user)
    denied = client.post(
        f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
        _payload(department, assignee='李四'),
        format='json',
    )
    assert denied.status_code == 403

    _grant(supervisor_user)
    instance.当前状态 = '在库'
    instance.save(update_fields=['当前状态'])
    rejected = client.post(
        f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
        _payload(department, assignee='李四'),
        format='json',
    )
    assert rejected.status_code == 400
    instance.refresh_from_db()
    assert instance.使用人 == '张三'
    assert not FixedAssetAssigneeChange.objects.filter(instance=instance).exists()


@pytest.mark.django_db
def test_draft_transfer_occupancy_blocks_handoff(supervisor_user, branch, department):
    from apps.assets.models import FixedAssetAssigneeChange
    from apps.transfers.models import Transfer, TransferLine, TransferLineInstance

    _grant(supervisor_user)
    instance = _instance(branch, department, 4)
    transfer = Transfer.objects.create(
        action_type=Transfer.ACTION_RETURN,
        调拨日期='2026-10-01',
        to_branch=branch,
        调入分公司=branch.name,
        审批状态='草稿',
        单据编号='GH-HANDOFF-001',
    )
    line = TransferLine.objects.create(transfer=transfer, item=instance.item, 行号=1, 数量=1)
    TransferLineInstance.objects.create(line=line, instance=instance)

    response = _client_for(supervisor_user).post(
        f'/api/assets/fixed-assets/{instance.pk}/change-assignee',
        _payload(department, assignee='李四'),
        format='json',
    )

    assert response.status_code == 400
    assert 'GH-HANDOFF-001' in str(response.data)
    instance.refresh_from_db()
    assert instance.使用人 == '张三'
    assert not FixedAssetAssigneeChange.objects.filter(instance=instance).exists()


@pytest.mark.django_db
def test_timeline_merges_transfer_and_assignee_events(admin_user, branch, department):
    from apps.assets.models import FixedAsset
    from apps.assets.services.instances import change_assignee
    from apps.categories.models import Category
    from apps.transfers.models import Transfer, TransferLine, TransferLineInstance

    item, _ = Category.objects.get_or_create(
        asset_code='HANDOFF-002',
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
        transfer=transfer, item=item, 行号=1, 数量=1, 使用人='张三', department=department,
    )
    TransferLineInstance.objects.create(line=line, instance=instance)
    change_assignee(
        instance_id=instance.pk, assignee='李四', department=department,
        operator=admin_user, reason='交接',
    )

    response = _client_for(admin_user).get(f'/api/assets/fixed-assets/{instance.pk}/timeline')

    assert response.status_code == 200
    rows = response.data['timeline']
    assert [row['kind'] for row in rows] == ['assignee_change', 'transfer']
    assert rows[0]['旧使用人'] == '张三'
    assert rows[0]['新使用人'] == '李四'
    assert rows[0]['新部门'] == department.name
    assert rows[0]['操作人'] == admin_user.name
