"""authz-write-scope-fixes 回归：三处越权写修复。

① batch-update 逐实例范围校验（范围外进 errors 不落库）
② 调拨单删除仅调出方可操作（perform_destroy 加守护）
③ 任命/免任仅 admin（组织 serializer 值变更校验，manage_organizations 不隐含任命权）
"""
import datetime

import pytest

from conftest import _client_for
from apps.assets.models import FixedAsset
from apps.transfers.models import Transfer, TransferLine
from apps.permissions.models import OperationGrant


def _grant(user, code):
    OperationGrant.objects.get_or_create(user=user, code=code)
    return user


@pytest.fixture
def item_instance(branch):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='固定', item_category='办公',
        asset_name='ThinkPad T14', asset_code='NB-AW1', unit='台',
        management_type='instance',
    )


def _instance(branch, item, doc_code, inner_code):
    t = Transfer.objects.create(
        单据编号=doc_code, 调拨日期=datetime.date(2026, 9, 28),
        调入分公司=branch.name, to_branch=branch,
        action_type='purchase', 审批状态='已入库',
    )
    line = TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=1)
    return FixedAsset.objects.create(
        item=item, 内部编号=inner_code, 当前状态='在库', branch=branch, birth_line=line,
    )


def _transfer_doc(from_branch, to_branch, code):
    return Transfer.objects.create(
        单据编号=code, 调拨日期=datetime.date(2026, 9, 28),
        调出分公司=from_branch.name, from_branch=from_branch,
        调入分公司=to_branch.name, to_branch=to_branch,
        action_type='transfer', 审批状态='待审批',
    )


@pytest.mark.django_db
class TestBatchUpdateScope:
    def test_out_of_scope_instance_rejected(self, supervisor_user, branch, second_branch, item_instance):
        _grant(supervisor_user, 'manage_instances')
        own = _instance(branch, item_instance, 'AS-S1', 'AS-S1')
        other = _instance(second_branch, item_instance, 'AS-S2', 'AS-S2')
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets/batch-update', {
            'ids': [str(own.pk), str(other.pk)], '备注': 'x',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['updated'] == 1
        assert resp.data['errors'] == [f'{other.内部编号}: 分公司不在授权范围']
        own.refresh_from_db()
        other.refresh_from_db()
        assert own.备注 == 'x'
        assert (other.备注 or '') == ''

    def test_admin_updates_across_branches(self, admin_user, branch, second_branch, item_instance):
        own = _instance(branch, item_instance, 'AS-A1', 'AS-A1')
        other = _instance(second_branch, item_instance, 'AS-A2', 'AS-A2')
        client = _client_for(admin_user)
        resp = client.post('/api/assets/fixed-assets/batch-update', {
            'ids': [str(own.pk), str(other.pk)], '备注': 'y',
        }, format='json')
        assert resp.status_code == 200 and resp.data['updated'] == 2 and resp.data['errors'] == []


@pytest.mark.django_db
class TestTransferDestroyScope:
    def test_to_branch_side_cannot_delete(self, supervisor_user, branch, second_branch):
        doc = _transfer_doc(second_branch, branch, 'TD-IN-1')
        client = _client_for(supervisor_user)
        resp = client.delete(f'/api/transfers/{doc.pk}')
        assert resp.status_code == 400
        assert '只读' in str(resp.data)
        assert Transfer.objects.filter(pk=doc.pk).exists()

    def test_from_branch_side_can_delete(self, admin_user, branch, second_branch):
        doc = _transfer_doc(second_branch, branch, 'TD-OUT-1')
        client = _client_for(admin_user)
        resp = client.delete(f'/api/transfers/{doc.pk}')
        assert resp.status_code == 204
        assert not Transfer.objects.filter(pk=doc.pk).exists()

    def test_non_transfer_delete_unaffected(self, supervisor_user, branch):
        doc = Transfer.objects.create(
            单据编号='TD-P1', 调拨日期=datetime.date(2026, 9, 28),
            调入分公司=branch.name, to_branch=branch,
            action_type='purchase', 审批状态='待审批',
        )
        client = _client_for(supervisor_user)
        resp = client.delete(f'/api/transfers/{doc.pk}')
        assert resp.status_code == 204
        assert not Transfer.objects.filter(pk=doc.pk).exists()


@pytest.mark.django_db
class TestAppointmentAdminOnly:
    def test_non_admin_cannot_change_branch_manager(self, supervisor_user, branch):
        _grant(supervisor_user, 'manage_organizations')
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/branches/{branch.pk}', {
            'manager': supervisor_user.pk,
        }, format='json')
        assert resp.status_code == 400
        assert '任命' in str(resp.data)
        branch.refresh_from_db()
        assert branch.manager is None

    def test_non_admin_unchanged_value_and_node_edit_pass(self, supervisor_user, branch, leader_user):
        from apps.organizations.models import Branch
        Branch.objects.filter(pk=branch.pk).update(manager=leader_user)
        _grant(supervisor_user, 'manage_organizations')
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/branches/{branch.pk}', {
            'manager': leader_user.pk, 'address': '新地址',
        }, format='json')
        assert resp.status_code == 200
        branch.refresh_from_db()
        assert branch.manager == leader_user and branch.address == '新地址'

    def test_admin_can_appoint(self, admin_user, branch, leader_user):
        client = _client_for(admin_user)
        resp = client.patch(f'/api/branches/{branch.pk}', {
            'manager': leader_user.pk,
        }, format='json')
        assert resp.status_code == 200
        branch.refresh_from_db()
        assert branch.manager == leader_user

    def test_non_admin_cannot_create_with_manager(self, supervisor_user, team):
        _grant(supervisor_user, 'manage_organizations')
        client = _client_for(supervisor_user)
        resp = client.post('/api/branches/', {
            'name': '越权新建', 'code': 'YQ001', 'team': team.pk,
            'manager': supervisor_user.pk,
        }, format='json')
        assert resp.status_code == 400
        assert '任命' in str(resp.data)

    def test_non_admin_cannot_change_team_leader(self, supervisor_user, team):
        _grant(supervisor_user, 'manage_organizations')
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/teams/{team.pk}', {
            'leader': supervisor_user.pk,
        }, format='json')
        assert resp.status_code == 400

    def test_non_admin_cannot_change_region_manager(self, supervisor_user, region):
        _grant(supervisor_user, 'manage_organizations')
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/regions/{region.pk}', {
            'manager': supervisor_user.pk,
        }, format='json')
        assert resp.status_code == 400
