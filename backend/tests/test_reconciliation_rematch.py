import pytest
from datetime import date
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.reconciliation.models import (
    ReconciliationComparison,
    ReconciliationIssue,
    ReconciliationOrderRow,
    ReconciliationTask,
    ReconciliationUploadVersion,
)
from apps.reconciliation.services import rematch_task
from apps.suppliers.models import Supplier
from conftest import _client_for


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(name='测试对账供应商')


def _make_task_with_version(supplier, admin_user, branch, period=None, row_count=2):
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=period or date(2026, 11, 1),
        created_by=admin_user, created_by_name=admin_user.name,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/test.xlsx', row_count=row_count,
    )
    for i in range(1, row_count + 1):
        ReconciliationOrderRow.objects.create(
            version=version, row_number=i, order_number=f'PO-{i:03d}',
            serial_original=f'SN-{i:04d}', serial_normalized=f'SN-{i:04d}',
            supplier_branch_text=branch.name, branch=branch,
            lease_start_date=date(2026, 11, 1), accounting_date=date(2026, 11, 1),
            billing_days=30, monthly_rent=Decimal('100.00'), month_amount=Decimal('100.00'),
        )
    task.current_version = version
    task.save(update_fields=['current_version'])
    return task, version


@pytest.mark.django_db
class TestRematch:
    def test_rematch_creates_new_version_reusing_orders(self, admin_user, branch, supplier):
        task, version1 = _make_task_with_version(supplier, admin_user, branch, row_count=2)
        v1_row_count = version1.order_rows.count()

        version_number = rematch_task(task, admin_user)

        task.refresh_from_db()
        assert version_number == 2
        assert task.current_version.version_number == 2
        v2 = task.current_version
        assert v2.order_rows.count() == v1_row_count
        assert list(v2.order_rows.values_list('serial_normalized', flat=True)) == \
            list(version1.order_rows.values_list('serial_normalized', flat=True))

    def test_rematch_idempotent_issues(self, admin_user, branch, supplier):
        task, version1 = _make_task_with_version(supplier, admin_user, branch, row_count=1)

        rematch_task(task, admin_user)
        task.refresh_from_db()
        issue_count_after_v2 = ReconciliationIssue.objects.filter(supplier=supplier).count()
        assert issue_count_after_v2 >= 1

        rematch_task(task, admin_user)
        task.refresh_from_db()
        assert ReconciliationIssue.objects.filter(supplier=supplier).count() == issue_count_after_v2

    def test_rematch_archived_rejected(self, admin_user, branch, supplier):
        task = ReconciliationTask.objects.create(
            supplier=supplier, period=date(2026, 11, 1),
            status=ReconciliationTask.STATUS_ARCHIVED,
            created_by=admin_user, created_by_name=admin_user.name,
        )
        version = ReconciliationUploadVersion.objects.create(
            task=task, version_number=1, file='reconciliation/test.xlsx', row_count=0,
        )
        task.current_version = version
        task.save(update_fields=['current_version'])

        with pytest.raises(ValidationError):
            rematch_task(task, admin_user)

    def test_rematch_permission(self, staff_user, branch, supplier):
        task = ReconciliationTask.objects.create(
            supplier=supplier, period=date(2026, 11, 1),
        )
        client = _client_for(staff_user)
        response = client.post(f'/api/reconciliation/tasks/{task.pk}/rematch')
        assert response.status_code == 403
