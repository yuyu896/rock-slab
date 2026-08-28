"""部门消耗统计报表（拆案第 10 案）：部门×月份×品目聚合、口径与数据范围。"""
from datetime import date

import pytest

from apps.transfers.models import Transfer, TransferLine
from conftest import _client_for


def _consumable(code, name):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '低值易耗品类', 'item_category': '办公耗材',
            'asset_name': name, 'unit': '包', 'management_type': 'consumable',
        },
    )
    return item


def _quantity_item(code, name):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '低值易耗品类', 'item_category': '办公耗材',
            'asset_name': name, 'unit': '个', 'management_type': 'quantity',
        },
    )
    return item


def _assign(branch, lines_spec, when, status='已通过'):
    """造领用单：lines_spec = [(item, qty, department)]。"""
    t = Transfer.objects.create(
        action_type='assign', 审批状态=status, 调拨日期=when,
        from_branch=branch, 调出分公司=branch.name,
    )
    for no, (item, qty, dept) in enumerate(lines_spec, start=1):
        TransferLine.objects.create(
            transfer=t, item=item, 行号=no, 数量=qty,
            department=dept, 使用人='张三',
        )
    return t


@pytest.mark.django_db
class TestConsumablesReport:
    def test_department_month_item_aggregation(self, authenticated_client, branch, department):
        paper = _consumable('CR-001', '打印纸')
        pen = _consumable('CR-002', '签字笔')
        _assign(branch, [(paper, 5, department)], date(2026, 8, 3))
        _assign(branch, [(paper, 3, department)], date(2026, 8, 20))
        _assign(branch, [(pen, 10, department)], date(2026, 8, 15))
        _assign(branch, [(paper, 2, department)], date(2026, 9, 2))

        resp = authenticated_client.get('/api/reports/consumables/')
        assert resp.status_code == 200
        data = resp.data
        assert data['months'] == ['2026-08', '2026-09']
        by_code = {r['code']: r for r in data['rows']}
        assert by_code['CR-001']['quantities'] == {'2026-08': 8, '2026-09': 2}
        assert by_code['CR-001']['total'] == 10
        assert by_code['CR-002']['quantities'] == {'2026-08': 10}
        assert by_code['CR-002']['total'] == 10
        assert by_code['CR-001']['department'] == department.name
        assert data['grandTotal'] == {'2026-08': 18, '2026-09': 2, 'total': 20}

    def test_non_consumable_and_inactive_excluded(self, authenticated_client, branch, department):
        paper = _consumable('CR-011', '打印纸')
        folder = _quantity_item('CR-012', '文件夹')
        _assign(branch, [(paper, 4, department), (folder, 2, department)], date(2026, 8, 5))
        _assign(branch, [(paper, 9, department)], date(2026, 8, 6), status='待审批')

        resp = authenticated_client.get('/api/reports/consumables/')
        assert resp.status_code == 200
        codes = [r['code'] for r in resp.data['rows']]
        assert codes == ['CR-011']  # 数量管理行与待审批单不计入
        assert resp.data['grandTotal']['total'] == 4

    def test_no_department_grouped_as_unassigned(self, authenticated_client, branch, department):
        paper = _consumable('CR-021', '打印纸')
        _assign(branch, [(paper, 4, None)], date(2026, 8, 5))
        _assign(branch, [(paper, 6, department)], date(2026, 8, 6))

        resp = authenticated_client.get('/api/reports/consumables/')
        by_dept = {r['department']: r for r in resp.data['rows']}
        assert set(by_dept) == {'未归属', department.name}
        assert by_dept['未归属']['total'] == 4
        assert by_dept[department.name]['total'] == 6

    def test_date_range_and_branch_filters(self, authenticated_client, branch, second_branch, department):
        paper = _consumable('CR-031', '打印纸')
        _assign(branch, [(paper, 3, department)], date(2026, 8, 10))
        _assign(branch, [(paper, 7, department)], date(2026, 7, 10))
        _assign(second_branch, [(paper, 99, None)], date(2026, 8, 10))

        resp = authenticated_client.get(
            '/api/reports/consumables/',
            {'dateRange': '2026-08-01,2026-08-31', 'branches': str(branch.id)},
        )
        assert resp.status_code == 200
        assert resp.data['months'] == ['2026-08']
        assert resp.data['grandTotal'] == {'2026-08': 3, 'total': 3}

    def test_scoped_user_sees_own_branch_only(self, supervisor_user, branch, second_branch, department):
        paper = _consumable('CR-041', '打印纸')
        _assign(branch, [(paper, 5, department)], date(2026, 8, 10))
        _assign(second_branch, [(paper, 50, None)], date(2026, 8, 10))

        client = _client_for(supervisor_user)
        resp = client.get('/api/reports/consumables/')
        assert resp.status_code == 200
        assert resp.data['grandTotal']['total'] == 5  # 第二分公司不在授权范围

    def test_scoped_user_branch_intersection(self, supervisor_user, branch, second_branch, department):
        paper = _consumable('CR-051', '打印纸')
        _assign(branch, [(paper, 5, department)], date(2026, 8, 10))
        _assign(second_branch, [(paper, 50, None)], date(2026, 8, 10))

        client = _client_for(supervisor_user)
        # 越权传入第二分公司 id：与授权范围取交集，仅统计授权内分公司
        resp = client.get(
            '/api/reports/consumables/',
            {'branches': f'{branch.id},{second_branch.id}'},
        )
        assert resp.status_code == 200
        assert resp.data['grandTotal']['total'] == 5
