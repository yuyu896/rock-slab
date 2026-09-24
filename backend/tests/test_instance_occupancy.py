"""
Tests for instance-picker-completeness（第二步）：未生效单据占用预检、占用映射端点、
内部编号/序列号搜索、报错单前缀。
"""
import pytest
from rest_framework import status

from apps.assets.models import FixedAsset
from apps.categories.models import Category
from apps.transfers.models import Transfer, TransferLine, TransferLineInstance


def _item(code, management_type='instance'):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '电子设备', 'item_category': '电脑',
            'asset_name': f'品目 {code}', 'unit': '台',
            'management_type': management_type,
        },
    )
    return item


def _mk_inst(branch, item, no, state='在库'):
    return FixedAsset.objects.create(
        item=item, 内部编号=f'{item.asset_code}-{branch.code}-{no}',
        当前状态=state, branch=branch,
    )


def _pending_assign(branch, item, insts, doc_status='待审批'):
    t = Transfer.objects.create(
        action_type='assign', 调拨日期='2026-09-24',
        from_branch=branch, 调出分公司=branch.name,
        审批状态=doc_status, 单据编号=f'LY-TEST-{insts[0].内部编号[-1:]}',
    )
    line = TransferLine.objects.create(transfer=t, item=item, 数量=len(insts), 行号=1)
    for inst in insts:
        TransferLineInstance.objects.create(line=line, instance=inst)
    return t


def _assign_payload(item, insts, branch):
    from apps.organizations.models import Department
    dept, _ = Department.objects.get_or_create(name='测试部门')
    return {
        '调拨日期': '2026-09-24', '调出分公司': branch.name,
        'items': [{
            'item': str(item.id), '数量': len(insts),
            'instances': [str(i.pk) for i in insts],
            '使用人': '张三', 'department': str(dept.id),
        }],
    }


@pytest.mark.django_db
class TestOccupancyPrecheck:
    def test_pending_occupation_rejected_at_create(self, authenticated_client, branch):
        item = _item('OC-1')
        a, b = _mk_inst(branch, item, 1), _mk_inst(branch, item, 2)
        _pending_assign(branch, item, [a])
        resp = authenticated_client.post('/api/transfers/assign', _assign_payload(item, [a, b], branch), format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '已被待审批单' in str(resp.data) and a.内部编号 in str(resp.data)
        assert Transfer.objects.filter(action_type='assign', 审批状态='待审批').count() == 1  # 未落库

    def test_rejected_doc_reference_not_occupying(self, authenticated_client, branch):
        item = _item('OC-2')
        a = _mk_inst(branch, item, 1)
        _pending_assign(branch, item, [a], doc_status='已驳回')
        resp = authenticated_client.post('/api/transfers/assign', _assign_payload(item, [a], branch), format='json')
        assert resp.status_code == status.HTTP_201_CREATED  # 驳回单引用不拦

    def test_draft_occupation_rejected(self, authenticated_client, branch):
        item = _item('OC-3')
        a = _mk_inst(branch, item, 1)
        _pending_assign(branch, item, [a], doc_status='草稿')
        resp = authenticated_client.post('/api/transfers/assign', _assign_payload(item, [a], branch), format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '已被草稿单' in str(resp.data)

    def test_edit_self_reference_not_blocked(self, authenticated_client, branch):
        """驳回后编辑重提：单据自身引用不构成对自己的占用。"""
        item = _item('OC-4')
        a = _mk_inst(branch, item, 1)
        t = _pending_assign(branch, item, [a], doc_status='已驳回')
        from apps.organizations.models import Department
        dept, _ = Department.objects.get_or_create(name='测试部门')
        resp = authenticated_client.patch(
            f'/api/transfers/{t.id}',
            {'调拨日期': '2026-09-24', '调出分公司': branch.name,
             'items': [{'item': str(item.id), '数量': 1, 'instances': [str(a.pk)],
                        '使用人': '李四', 'department': str(dept.id)}]},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK, getattr(resp, 'data', None)


@pytest.mark.django_db
class TestOccupancyEndpoint:
    def test_instance_occupancy_map(self, authenticated_client, branch):
        item = _item('OC-5')
        a, b = _mk_inst(branch, item, 1), _mk_inst(branch, item, 2)
        t = _pending_assign(branch, item, [a])
        resp = authenticated_client.get('/api/transfers/instance-occupancy', {
            'branch': branch.name, 'asset_code': item.asset_code,
        })
        assert resp.status_code == status.HTTP_200_OK
        rows = resp.data
        assert len(rows) == 1
        assert rows[0]['instanceId'] == str(a.pk)
        assert rows[0]['docNo'] == t.单据编号 and rows[0]['docStatus'] == '待审批'


@pytest.mark.django_db
class TestInnerKeywordSearch:
    def test_inner_keyword_filters_code_and_serial(self, authenticated_client, branch):
        item = _item('OC-6')
        a = _mk_inst(branch, item, 11)
        b = FixedAsset.objects.create(
            item=item, 内部编号=f'{item.asset_code}-{branch.code}-22',
            当前状态='在库', branch=branch, 序列号='SN-XYZ-9',
        )
        r1 = authenticated_client.get('/api/assets/fixed-assets', {
            'asset_code': item.asset_code, 'inner_keyword': '-22',
        })
        codes1 = [r['内部编号'] for r in r1.data['results']]
        assert codes1 == [b.内部编号]
        r2 = authenticated_client.get('/api/assets/fixed-assets', {
            'asset_code': item.asset_code, 'inner_keyword': 'SN-XYZ',
        })
        codes2 = [r['内部编号'] for r in r2.data['results']]
        assert codes2 == [b.内部编号]


@pytest.mark.django_db
class TestSingleLineContextPrefix:
    def test_instance_error_single_prefix(self, authenticated_client, branch):
        """占用冲突类报错单层前缀（修复前重复两遍）。"""
        from apps.assets.services import ledger
        item = _item('OC-7', 'instance')
        _mk_inst(branch, item, 1, state='在库')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 1, '造数')
        # 建一张待审批调拨占住在库实例 → 审批通过后状态在库不变（调拨转分公司）
        # 直接构造状态不符：领用在库实例审批在用时冲突——用归还路径最快：归还要求在用，给在库实例
        t = Transfer.objects.create(
            action_type='return', 调拨日期='2026-09-24',
            to_branch=branch, 调入分公司=branch.name, 审批状态='待审批', 单据编号='GH-TEST-1',
        )
        inst = FixedAsset.objects.get(item=item)
        line = TransferLine.objects.create(transfer=t, item=item, 数量=1, 行号=1)
        TransferLineInstance.objects.create(line=line, instance=inst)
        resp = authenticated_client.post(f'/api/transfers/{t.id}/approve', {'approved': True}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        detail = str(resp.data['detail'])
        assert detail.count('明细行') == 1  # 单层前缀
        assert '状态 在库 不是 在用' in detail
