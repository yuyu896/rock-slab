import pytest
from apps.reconciliation.models import ReconciliationIssue

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
