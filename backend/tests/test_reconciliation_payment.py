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

    def test_unconcluded_diff_in_pending(self, admin_user, branch, supplier):
        """未结论差异行（conclusion_type=''）计入 pending，不计 confirmed."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='300.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-pending-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='',
            status=ReconciliationIssue.STATUS_OPEN,
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

    def test_concluded_diff_in_confirmed(self, admin_user, branch, supplier):
        """conclusion_type 非空的差异行计入 confirmed_amount."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='200.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-concluded-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='supplier_overbilled',
            status=ReconciliationIssue.STATUS_OPEN,
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
        assert Decimal(data['confirmed_amount']) == Decimal('200.00')
        assert Decimal(data['pending_amount']) == Decimal('0.00')
        assert data['can_archive'] is True

    def test_can_archive_requires_zero_pending(self, admin_user, branch, supplier):
        """pending=0 时 can_archive=True；pending>0 时 can_archive=False."""
        task, version = _make_task_with_version(supplier)

        # Matched row (confirmed)
        row1 = _make_order_row(version, branch, row_number=1, amount='100.00')
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=row1,
        )

        # Open unconcluded diff (pending)
        row2 = _make_order_row(version, branch, row_number=2, amount='50.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-archive-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='',
            status=ReconciliationIssue.STATUS_OPEN,
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

        # Resolve the issue (set conclusion_type)
        issue.conclusion_type = 'period_adjustment'
        issue.save(update_fields=['conclusion_type'])

        response2 = client.get(f'/api/reconciliation/tasks/{task.pk}/payment')
        assert response2.status_code == 200
        assert response2.data['can_archive'] is True
        assert Decimal(response2.data['confirmed_amount']) == Decimal('150.00')
        assert Decimal(response2.data['pending_amount']) == Decimal('0.00')

    def test_rows_contains_all_comparisons(self, admin_user, branch, supplier):
        """rows 包含所有 comparison 行（matched + diff）."""
        task, version = _make_task_with_version(supplier)
        row1 = _make_order_row(version, branch, row_number=1, amount='100.00')
        row2 = _make_order_row(version, branch, row_number=2, amount='200.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-rows-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='',
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
        assert len(response.data['rows']) == 2
        serials = {r['serial'] for r in response.data['rows']}
        assert 'SN-001' in serials
        assert 'SN-002' in serials

    def test_not_recurred_unconcluded_in_pending(self, admin_user, branch, supplier):
        """not_recurred 状态且无结论的差异行也计入 pending."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='150.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-notrecurred-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='',
            status=ReconciliationIssue.STATUS_NOT_RECURRED,
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
        assert Decimal(response.data['pending_amount']) == Decimal('150.00')
        assert response.data['can_archive'] is False

    def test_archive_gate_blocks_when_pending(self, admin_user, branch, supplier):
        """归档时若有未处理差异应被拒绝."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='100.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-archivegate-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='',
            status=ReconciliationIssue.STATUS_OPEN,
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

    def test_archive_gate_passes_when_no_pending(self, admin_user, branch, supplier):
        """归档时若无未处理差异应允许通过."""
        task, version = _make_task_with_version(supplier)
        order_row = _make_order_row(version, branch, row_number=1, amount='100.00')
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='pay-archivegate-pass-test',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='supplier_overbilled',
            status=ReconciliationIssue.STATUS_OPEN,
        )
        ReconciliationComparison.objects.create(
            version=version,
            result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=order_row,
            issue=issue,
        )

        client = _client_for(admin_user)
        response = client.post(f'/api/reconciliation/tasks/{task.pk}/archive')
        assert response.status_code == 200

    def test_payment_export(self, admin_user, branch, supplier):
        """?type=payment 导出 Excel，包含正确列标题."""
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
        assert '结论' in headers
        # Should have data row
        assert ws.max_row >= 2
