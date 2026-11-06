import pytest
from datetime import date
from decimal import Decimal

from apps.reconciliation.models import (
    ReconciliationComparison,
    ReconciliationIssue,
    ReconciliationOrderRow,
    ReconciliationTask,
    ReconciliationUploadVersion,
)
from apps.suppliers.models import Supplier
from conftest import _client_for


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(name='付款测试供应商')


def _make_task_with_version(supplier, period=None):
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=period or date(2026, 11, 1),
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/test.xlsx', row_count=0,
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    return task, version


def _make_order_row(version, branch, row_number=1, amount='100.00', rent='100.00'):
    return ReconciliationOrderRow.objects.create(
        version=version, row_number=row_number,
        order_number=f'PO-{row_number}', serial_original=f'SN-{row_number:03d}',
        serial_normalized=f'SN-{row_number:03d}', supplier_branch_text=branch.name,
        branch=branch, lease_start_date=date(2026, 11, 1),
        accounting_date=date(2026, 11, 1), billing_days=30,
        monthly_rent=Decimal(rent), month_amount=Decimal(amount),
    )


@pytest.mark.django_db
class TestPaymentSummary:
    def test_matched_rows_in_confirmed(self, admin_user, branch, supplier):
        """匹配行金额计入 confirmed_amount."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='500.00')
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=order_row,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/payment')

        assert response.status_code == 200
        data = response.data
        assert Decimal(data['confirmed_amount']) == Decimal('500.00')
        assert Decimal(data['pending_amount']) == Decimal('0.00')
        assert Decimal(data['total_amount']) == Decimal('500.00')
        assert data['can_archive'] is True
        assert len(data['branches']) == 1
        assert data['branches'][0]['branch_name'] == branch.name
        assert len(data['branches'][0]['rows']) == 1

    def test_diff_row_in_pending(self, admin_user, branch, supplier):
        """差异行金额计入 pending_amount."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='300.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-pending-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
        )
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=order_row,
            issue=issue,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/payment')

        assert response.status_code == 200
        data = response.data
        assert Decimal(data['confirmed_amount']) == Decimal('0.00')
        assert Decimal(data['pending_amount']) == Decimal('300.00')
        assert Decimal(data['total_amount']) == Decimal('300.00')
        assert data['can_archive'] is False

    def test_can_archive_requires_zero_diffs(self, admin_user, branch, supplier):
        """can_archive=False 时有差异；所有行匹配时 can_archive=True."""
        task, version = _make_task_with_version(supplier)

        row1 = _make_order_row(version, branch, row_number=1, amount='100.00')
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=row1,
        )
        row2 = _make_order_row(version, branch, row_number=2, amount='50.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-archive-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
        )
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=row2,
            issue=issue,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/payment')
        assert response.status_code == 200
        assert response.data['can_archive'] is False
        assert Decimal(response.data['confirmed_amount']) == Decimal('100.00')
        assert Decimal(response.data['pending_amount']) == Decimal('50.00')

    def test_branches_contains_all_rows(self, admin_user, branch, supplier):
        """branches[].rows 包含所有 comparison 行（matched + diff）."""
        task, version = _make_task_with_version(supplier)
        row1 = _make_order_row(version, branch, row_number=1, amount='100.00')
        row2 = _make_order_row(version, branch, row_number=2, amount='200.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-rows-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
        )
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=row1,
        )
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=row2,
            issue=issue,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/payment')
        assert response.status_code == 200
        assert len(response.data['branches']) == 1
        rows = response.data['branches'][0]['rows']
        assert len(rows) == 2
        serials = {r['serial'] for r in rows}
        assert 'SN-001' in serials
        assert 'SN-002' in serials

    def test_archive_gate_blocks_when_diff_present(self, admin_user, branch, supplier):
        """归档时若有差异应被拒绝."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='100.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-archivegate-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
        )
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=order_row,
            issue=issue,
        )

        client = _client_for(admin_user)
        response = client.post(f'/api/reconciliation/tasks/{task.pk}/archive')
        assert response.status_code == 400

    def test_archive_gate_passes_when_all_matched(self, admin_user, branch, supplier):
        """归档时若无差异应允许通过."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='100.00')
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=order_row,
        )

        client = _client_for(admin_user)
        response = client.post(f'/api/reconciliation/tasks/{task.pk}/archive')
        assert response.status_code == 200

    def test_payment_export(self, admin_user, branch, supplier):
        """?type=payment 导出 Excel，包含正确列标题。"""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='100.00')
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=order_row,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/export?task={task.pk}&type=payment')
        assert response.status_code == 200
        assert response['Content-Type'].startswith(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        from io import BytesIO
        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(response.content))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        assert '序列号' in headers
        assert '分公司' in headers
        assert '本月金额' in headers
        assert '结论' not in headers
        assert ws.max_row >= 2

    def test_system_duplicate_amount_counted_once(self, admin_user, branch, supplier):
        """system_duplicate: N 个系统实例共享一个 order_row，金额只计一次。"""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='100.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-dup-test',
            issue_type=ReconciliationComparison.RESULT_SYSTEM_DUPLICATE,
            first_period=task.period, last_period=task.period,
        )
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_DUPLICATE,
            order_row=order_row, issue=issue, internal_code='DUP-1',
        )
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_DUPLICATE,
            order_row=order_row, issue=issue, internal_code='DUP-2',
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/payment')
        assert response.status_code == 200
        data = response.data
        assert Decimal(data['pending_amount']) == Decimal('100.00')
        assert Decimal(data['confirmed_amount']) == Decimal('0.00')
        assert Decimal(data['total_amount']) == Decimal('100.00')

        response2 = client.get(f'/api/reconciliation/tasks/{task.pk}/branch-summary')
        assert response2.status_code == 200
        summary = response2.data
        assert len(summary) == 1
        assert summary[0]['order_count'] == 1
        assert summary[0]['diff_count'] == 1
        assert Decimal(summary[0]['month_amount']) == Decimal('0.00')

    def test_multi_branch_structure(self, admin_user, branch, second_branch, supplier):
        """branches[] 按分公司分组，每组有独立汇总金额."""
        task, version = _make_task_with_version(supplier)
        row_a = _make_order_row(version, branch, row_number=1, amount='100.00')
        row_b = _make_order_row(version, second_branch, row_number=2, amount='200.00')
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_MATCHED, order_row=row_a,
        )
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='multi-branch-issue',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
        )
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=row_b, issue=issue,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/payment')
        assert response.status_code == 200
        data = response.data
        assert len(data['branches']) == 2
        branch_map = {b['branch_id']: b for b in data['branches']}
        assert Decimal(branch_map[str(branch.pk)]['confirmed_amount']) == Decimal('100.00')
        assert Decimal(branch_map[str(second_branch.pk)]['pending_amount']) == Decimal('200.00')
        assert data['can_archive'] is False
