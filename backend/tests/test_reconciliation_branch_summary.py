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
from apps.users.models import User
from apps.permissions.models import ManagementScope, OperationGrant
from conftest import _client_for


@pytest.mark.django_db
class TestBranchSummary:
    def _make_task_version(self, supplier, period=None):
        task = ReconciliationTask.objects.create(
            supplier=supplier, period=period or date(2026, 11, 1),
        )
        version = ReconciliationUploadVersion.objects.create(
            task=task, version_number=1, file='reconciliation/test.xlsx', row_count=0,
        )
        task.current_version = version
        task.save(update_fields=['current_version'])
        return task, version

    def _make_order_row(self, version, branch, row_number=1, amount='100.00'):
        return ReconciliationOrderRow.objects.create(
            version=version, row_number=row_number,
            order_number=f'PO-{row_number}', serial_original=f'SN-{row_number}',
            serial_normalized=f'SN-{row_number}', supplier_branch_text=branch.name,
            branch=branch, lease_start_date=date(2026, 11, 1),
            accounting_date=date(2026, 11, 1), billing_days=30,
            monthly_rent=Decimal(amount), month_amount=Decimal(amount),
        )

    def test_summary_returns_per_branch_counts(self, admin_user, branch, second_branch):
        supplier = Supplier.objects.create(name='汇总测试供应商')
        task, version = self._make_task_version(supplier)

        # branch A: one matched row
        row_a = self._make_order_row(version, branch, row_number=1, amount='100.00')
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=row_a,
        )

        # branch B: one diff (order_only) row with an open issue
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='bs-test-key',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
        )
        row_b = self._make_order_row(version, second_branch, row_number=2, amount='200.00')
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=row_b, issue=issue,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/branch-summary')

        assert response.status_code == 200
        data = {row['branch_id']: row for row in response.data}
        assert len(data) == 2

        row_a_data = data[str(branch.pk)]
        assert row_a_data['order_count'] == 1
        assert row_a_data['matched_count'] == 1
        assert row_a_data['diff_count'] == 0
        assert row_a_data['pending_count'] == 0
        assert row_a_data['month_amount'] == '100.00'

        row_b_data = data[str(second_branch.pk)]
        assert row_b_data['order_count'] == 1
        assert row_b_data['matched_count'] == 0
        assert row_b_data['diff_count'] == 1
        assert row_b_data['pending_count'] == 1
        assert row_b_data['month_amount'] == '0.00'

    def test_summary_pending_uses_conclusion_type(self, admin_user, branch):
        supplier = Supplier.objects.create(name='结论类型测试供应商')
        task, version = self._make_task_version(supplier)

        # diff with conclusion_type set -> NOT pending
        issue_resolved = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='ct-resolved',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='supplier_overbilled',
        )
        row1 = self._make_order_row(version, branch, row_number=1)
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=row1, issue=issue_resolved,
        )

        # diff with empty conclusion_type -> IS pending
        issue_pending = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='ct-pending',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
            conclusion_type='',
        )
        row2 = self._make_order_row(version, branch, row_number=2)
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=row2, issue=issue_pending,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/branch-summary')

        assert response.status_code == 200
        assert len(response.data) == 1
        row = response.data[0]
        assert row['diff_count'] == 2
        assert row['pending_count'] == 1

    def test_summary_scope_filtered(self, branch, second_branch):
        supplier = Supplier.objects.create(name='范围过滤汇总供应商')
        task, version = self._make_task_version(supplier)

        # One matched comparison in branch (visible)
        row_a = self._make_order_row(version, branch, row_number=1)
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_MATCHED,
            order_row=row_a,
        )

        # One diff comparison in second_branch (should be hidden)
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='scope-test-key',
            issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            first_period=task.period, last_period=task.period,
        )
        row_b = self._make_order_row(version, second_branch, row_number=2)
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            order_row=row_b, issue=issue,
        )

        # User scoped only to branch, with view_reconciliation + view_suppliers
        scoped_user = User.objects.create_user(
            phone='13800098765', name='范围受限用户', password='test123456',
            role='manager', status='active',
        )
        ManagementScope.objects.create(user=scoped_user, branch=branch)
        OperationGrant.objects.create(user=scoped_user, code='view_reconciliation')
        OperationGrant.objects.create(user=scoped_user, code='view_suppliers')

        client = _client_for(scoped_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/branch-summary')

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['branch_id'] == str(branch.pk)
        assert response.data[0]['matched_count'] == 1

    def test_summary_no_version_returns_empty(self, admin_user, branch):
        supplier = Supplier.objects.create(name='无版本供应商')
        task = ReconciliationTask.objects.create(
            supplier=supplier, period=date(2026, 11, 1),
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/branch-summary')

        assert response.status_code == 200
        assert response.data == []

    def test_summary_system_only_uses_system_branch(self, admin_user, branch):
        supplier = Supplier.objects.create(name='系统侧分公司供应商')
        task, version = self._make_task_version(supplier)

        # system_only comparison with no order_row, only system_branch
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='sys-only-key',
            issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
            first_period=task.period, last_period=task.period,
        )
        ReconciliationComparison.objects.create(
            version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
            issue=issue, system_serial_original='SYS-SN',
            system_branch_id=branch.pk, system_branch_name=branch.name,
        )

        client = _client_for(admin_user)
        response = client.get(f'/api/reconciliation/tasks/{task.pk}/branch-summary')

        assert response.status_code == 200
        assert len(response.data) == 1
        row = response.data[0]
        assert row['branch_id'] == str(branch.pk)
        assert row['branch_name'] == branch.name
        assert row['order_count'] == 1
        assert row['diff_count'] == 1
        assert row['matched_count'] == 0
        assert row['pending_count'] == 1
