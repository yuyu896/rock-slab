"""
Tests for transfer-instance-renumber：调拨生效空号补位换号 + 前编号快照 + 存量补齐命令。
"""
import pytest
from rest_framework import status

from apps.assets.models import FixedAsset, InstanceSequence
from apps.assets.services import ledger
from apps.transfers.models import Transfer, TransferLine, TransferLineInstance


def _item(code, management_type='instance'):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': management_type,
        },
    )
    return item


def _seed(branch, item, stock=0):
    if stock:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '测试造数')


def _mk_inst(branch, item, no, state='在库'):
    """按分公司段格式直造实例（tests 在架构白名单内）。"""
    return FixedAsset.objects.create(
        item=item, 内部编号=f'{item.asset_code}-{branch.code}-{no}',
        当前状态=state, branch=branch,
    )


def _set_seq(branch, item, last_no):
    InstanceSequence.objects.update_or_create(
        item=item, branch=branch, defaults={'last_no': last_no},
    )


def _create_transfer(client, from_branch, to_branch, item, instances):
    payload = {
        '调拨日期': '2026-09-23',
        '调出分公司': from_branch.name,
        '调入分公司': to_branch.name,
        'items': [{
            'item': str(item.id), '数量': len(instances),
            'instances': [str(i.id) for i in instances],
        }],
    }
    resp = client.post('/api/transfers/transfer', payload, format='json')
    assert resp.status_code == status.HTTP_201_CREATED
    return resp.data['id']


def _approve(client, tid, approved=True):
    return client.post(f'/api/transfers/{tid}/approve', {'approved': approved}, format='json')


@pytest.mark.django_db
class TestTransferRenumberOnApproval:
    def test_approve_append_when_no_gap(self, authenticated_client, branch, second_branch):
        item = _item('RN-001')
        _seed(branch, item, stock=1)
        inst = _mk_inst(branch, item, 1)
        for no in (1, 2, 3):
            _mk_inst(second_branch, item, no)
        _set_seq(second_branch, item, 3)

        tid = _create_transfer(authenticated_client, branch, second_branch, item, [inst])
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == status.HTTP_200_OK

        inst.refresh_from_db()
        assert inst.branch_id == second_branch.id
        assert inst.内部编号 == 'RN-001-RG2001-4'
        lnk = TransferLineInstance.objects.get(instance=inst)
        assert lnk.调拨前编号 == 'RN-001-CS001-1'
        assert InstanceSequence.objects.get(item=item, branch=second_branch).last_no == 4

    def test_approve_fills_smallest_gap(self, authenticated_client, branch, second_branch):
        item = _item('RN-002')
        _seed(branch, item, stock=1)
        inst = _mk_inst(branch, item, 1)
        for no in (1, 2, 4):  # 缺 3
            _mk_inst(second_branch, item, no)
        _set_seq(second_branch, item, 4)

        tid = _create_transfer(authenticated_client, branch, second_branch, item, [inst])
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == status.HTTP_200_OK

        inst.refresh_from_db()
        assert inst.内部编号 == 'RN-002-RG2001-3'  # 顶最小空号
        assert InstanceSequence.objects.get(item=item, branch=second_branch).last_no == 4  # 计数器不动

    def test_multi_instances_same_line_distinct_numbers(self, authenticated_client, branch, second_branch):
        item = _item('RN-003')
        _seed(branch, item, stock=2)
        i1, i2 = _mk_inst(branch, item, 1), _mk_inst(branch, item, 2)
        for no in (1, 2):
            _mk_inst(second_branch, item, no)
        _set_seq(second_branch, item, 2)

        tid = _create_transfer(authenticated_client, branch, second_branch, item, [i1, i2])
        resp = _approve(authenticated_client, tid)
        assert resp.status_code == status.HTTP_200_OK

        i1.refresh_from_db()
        i2.refresh_from_db()
        assert {i1.内部编号, i2.内部编号} == {'RN-003-RG2001-3', 'RN-003-RG2001-4'}
        assert i1.内部编号 != i2.内部编号

    def test_reject_keeps_code(self, authenticated_client, branch, second_branch):
        item = _item('RN-004')
        _seed(branch, item, stock=1)
        inst = _mk_inst(branch, item, 1)
        tid = _create_transfer(authenticated_client, branch, second_branch, item, [inst])
        resp = _approve(authenticated_client, tid, approved=False)
        assert resp.status_code == status.HTTP_200_OK

        inst.refresh_from_db()
        assert inst.内部编号 == 'RN-004-CS001-1'
        assert inst.branch_id == branch.id
        assert not TransferLineInstance.objects.filter(instance=inst, 调拨前编号__gt='').exists()

    def test_assign_keeps_code(self, authenticated_client, branch, item_id, department):
        from apps.organizations.models import Department
        item = _item('RN-005')
        _seed(branch, item, stock=1)
        inst = _mk_inst(branch, item, 1)
        dept, _ = Department.objects.get_or_create(name='测试部门')
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-09-23', '调出分公司': branch.name, '调入分公司': branch.name,
            'items': [{'item': str(item.id), '数量': 1, 'instances': [str(inst.id)],
                       '使用人': '张三', 'department': str(dept.id)}],
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        resp = _approve(authenticated_client, resp.data['id'])
        assert resp.status_code == status.HTTP_200_OK
        inst.refresh_from_db()
        assert inst.内部编号 == 'RN-005-CS001-1'
        assert inst.当前状态 == '在用'


@pytest.mark.django_db
class TestRenumberCommand:
    def _make_drift(self, branch, second_branch, item):
        """造漂号实例：编号挂 CS001 段、实例已属第二分公司、有生效调拨流水。"""
        inst = FixedAsset.objects.create(
            item=item, 内部编号=f'{item.asset_code}-{branch.code}-9',
            当前状态='在库', branch=second_branch,
        )
        t = Transfer.objects.create(
            action_type='transfer', 调拨日期='2026-09-18',
            from_branch=branch, to_branch=second_branch,
            调出分公司=branch.name, 调入分公司=second_branch.name, 审批状态='已通过',
        )
        line = TransferLine.objects.create(transfer=t, item=item, 数量=1, 行号=1)
        TransferLineInstance.objects.create(line=line, instance=inst)
        return inst, t, line

    def test_preview_confirm_idempotent(self, branch, second_branch):
        from django.core.management import call_command
        from io import StringIO
        item = _item('RN-CMD')
        inst, t, line = self._make_drift(branch, second_branch, item)
        for no in (1, 2):
            _mk_inst(second_branch, item, no)
        _set_seq(second_branch, item, 2)

        out = StringIO()
        call_command('renumber_transfer_instances', stdout=out)
        assert 'RN-CMD-CS001-9 → RN-CMD-RG2001-3' in out.getvalue()
        inst.refresh_from_db()
        assert inst.内部编号 == 'RN-CMD-CS001-9'  # 预览零落库

        out = StringIO()
        call_command('renumber_transfer_instances', '--confirm', stdout=out)
        inst.refresh_from_db()
        assert inst.内部编号 == 'RN-CMD-RG2001-3'
        lnk = TransferLineInstance.objects.get(instance=inst)
        assert lnk.调拨前编号 == 'RN-CMD-CS001-9'

        out = StringIO()
        call_command('renumber_transfer_instances', stdout=out)
        assert '无需处理' in out.getvalue()  # 幂等

    def test_no_flow_drift_untouched(self, branch, second_branch):
        """无生效调拨流水的漂号实例（纯历史导入）不碰。"""
        from django.core.management import call_command
        from io import StringIO
        item = _item('RN-NOFLOW')
        FixedAsset.objects.create(
            item=item, 内部编号=f'{item.asset_code}-{branch.code}-1',
            当前状态='在库', branch=second_branch,
        )
        out = StringIO()
        call_command('renumber_transfer_instances', stdout=out)
        assert '无需处理' in out.getvalue()
