import pytest
from datetime import date

from apps.reconciliation.models import (
    ReconciliationIssue, ReconciliationTask,
)
from apps.reconciliation.services import update_issue
from apps.suppliers.models import Supplier
from conftest import _client_for


@pytest.mark.django_db
class TestConclusionType:
    def test_conclusion_choices_has_five_types(self):
        codes = [code for code, _ in ReconciliationIssue.CONCLUSION_CHOICES]
        assert codes == [
            'system_not_registered', 'serial_corrected',
            'supplier_overbilled', 'supplier_underbilled',
            'period_adjustment',
        ]

    def test_default_empty(self, branch):
        from apps.suppliers.models import Supplier
        from apps.reconciliation.models import ReconciliationTask
        from datetime import date
        supplier = Supplier.objects.create(name='测试供应商')
        task = ReconciliationTask.objects.create(supplier=supplier, period=date(2026, 11, 1))
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='k1', issue_type='order_only',
            first_period=task.period, last_period=task.period,
        )
        assert issue.conclusion_type == ''

    def test_invalid_choice_rejected(self):
        from django.core.exceptions import ValidationError
        issue = ReconciliationIssue(
            supplier_id=None, issue_key='x', issue_type='order_only',
            first_period='2026-11-01', last_period='2026-11-01',
            conclusion_type='bogus',
        )
        with pytest.raises(ValidationError):
            issue.full_clean()

    def test_update_issue_conclusion_type(self, admin_user, branch):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        supplier = Supplier.objects.create(name='结论类型测试供应商')
        task = ReconciliationTask.objects.create(supplier=supplier, period=date(2026, 11, 1))
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='ct-test-001', issue_type='order_only',
            first_period=task.period, last_period=task.period,
        )

        # PATCH conclusion_type via service — sets the field
        update_issue(issue, admin_user, conclusion_type='system_not_registered')
        issue.refresh_from_db()
        assert issue.conclusion_type == 'system_not_registered'

        # PATCH conclusion_type='' clears it
        update_issue(issue, admin_user, conclusion_type='')
        issue.refresh_from_db()
        assert issue.conclusion_type == ''

        # Invalid value raises ValidationError
        with pytest.raises(DRFValidationError):
            update_issue(issue, admin_user, conclusion_type='invalid_value')

    def test_patch_conclusion_type_via_api(self, admin_user, branch):
        supplier = Supplier.objects.create(name='API结论类型供应商')
        task = ReconciliationTask.objects.create(supplier=supplier, period=date(2026, 11, 1))
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='ct-api-001', issue_type='order_only',
            first_period=task.period, last_period=task.period,
        )
        from apps.permissions.models import ManagementScope, OperationGrant
        ManagementScope.objects.create(user=admin_user, branch=branch)
        OperationGrant.objects.create(user=admin_user, code='manage_reconciliation')
        client = _client_for(admin_user)

        resp = client.patch(
            f'/api/reconciliation/issues/{issue.pk}',
            {'conclusionType': 'supplier_overbilled'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['conclusion_type'] == 'supplier_overbilled'

        issue.refresh_from_db()
        assert issue.conclusion_type == 'supplier_overbilled'

        # Invalid value via API returns 400
        resp_bad = client.patch(
            f'/api/reconciliation/issues/{issue.pk}',
            {'conclusionType': 'bogus_value'},
            format='json',
        )
        assert resp_bad.status_code == 400

    def test_history_records_conclusion_type(self, admin_user, branch):
        from apps.reconciliation.models import ReconciliationIssueHistory
        supplier = Supplier.objects.create(name='历史追踪测试供应商')
        task = ReconciliationTask.objects.create(supplier=supplier, period=date(2026, 11, 1))
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='hist-001', issue_type='order_only',
            first_period=task.period, last_period=task.period,
        )

        update_issue(issue, admin_user, conclusion_type='supplier_overbilled')
        update_issue(issue, admin_user, conclusion_type='period_adjustment')

        history = list(ReconciliationIssueHistory.objects.filter(issue=issue).order_by('created_at'))
        assert len(history) == 2
        assert history[0].old_conclusion_type == ''
        assert history[0].new_conclusion_type == 'supplier_overbilled'
        assert history[1].old_conclusion_type == 'supplier_overbilled'
        assert history[1].new_conclusion_type == 'period_adjustment'

        update_issue(issue, admin_user, conclusion_type='')
        latest = ReconciliationIssueHistory.objects.filter(issue=issue).order_by('-created_at').first()
        assert latest.old_conclusion_type == 'period_adjustment'
        assert latest.new_conclusion_type == ''
