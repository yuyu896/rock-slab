import uuid

from django.conf import settings
from django.db import models

from core.models import TimestampedModel, UUIDModel


class ReconciliationTask(UUIDModel, TimestampedModel):
    STATUS_DRAFT = 'draft'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [(STATUS_DRAFT, '未归档'), (STATUS_ARCHIVED, '已归档')]

    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.PROTECT, related_name='reconciliation_tasks')
    period = models.DateField('对账月份')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    current_version = models.ForeignKey(
        'ReconciliationUploadVersion', on_delete=models.PROTECT, null=True, blank=True,
        related_name='active_for_tasks',
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reconciliation_tasks')
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='archived_reconciliation_tasks',
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reconciliation_task'
        ordering = ['-period', 'supplier__name']
        constraints = [models.UniqueConstraint(fields=['supplier', 'period'], name='uniq_recon_supplier_period')]


def reconciliation_upload_path(instance, filename):
    return f'reconciliation/{instance.task_id}/{instance.version_number}/{filename}'


class ReconciliationUploadVersion(UUIDModel, TimestampedModel):
    task = models.ForeignKey(ReconciliationTask, on_delete=models.PROTECT, related_name='versions')
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=reconciliation_upload_path)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    row_count = models.PositiveIntegerField(default=0)
    calculation_warnings = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'reconciliation_upload_version'
        ordering = ['-version_number']
        constraints = [models.UniqueConstraint(fields=['task', 'version_number'], name='uniq_recon_task_version')]


class ReconciliationOrderRow(UUIDModel):
    version = models.ForeignKey(ReconciliationUploadVersion, on_delete=models.PROTECT, related_name='order_rows')
    row_number = models.PositiveIntegerField()
    order_number = models.CharField(max_length=200, blank=True, default='')
    serial_original = models.CharField(max_length=200)
    serial_normalized = models.CharField(max_length=200, db_index=True)
    supplier_branch_text = models.CharField(max_length=100)
    branch = models.ForeignKey('organizations.Branch', on_delete=models.PROTECT, related_name='reconciliation_rows')
    lease_start_date = models.DateField()
    accounting_date = models.DateField()
    billing_days = models.PositiveSmallIntegerField()
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2)
    month_amount = models.DecimalField(max_digits=12, decimal_places=2)
    uploaded_billing_days = models.PositiveSmallIntegerField(null=True, blank=True)
    uploaded_month_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'reconciliation_order_row'
        ordering = ['row_number']
        constraints = [models.UniqueConstraint(fields=['version', 'row_number'], name='uniq_recon_version_row')]


class ReconciliationIssue(UUIDModel, TimestampedModel):
    STATUS_OPEN = 'open'
    STATUS_NOT_RECURRED = 'not_recurred'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, '待处理'), (STATUS_NOT_RECURRED, '本期未重现'), (STATUS_CLOSED, '已结案'),
    ]

    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.PROTECT, related_name='reconciliation_issues')
    issue_key = models.CharField(max_length=64, unique=True)
    issue_type = models.CharField(max_length=32)
    serial_normalized = models.CharField(max_length=200, blank=True, default='')
    first_period = models.DateField()
    last_period = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    conclusion = models.CharField(max_length=100, blank=True, default='')
    note = models.TextField(blank=True, default='')
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    handled_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='closed_reconciliation_issues',
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reconciliation_issue'
        indexes = [models.Index(fields=['supplier', 'status', 'last_period'])]


class ReconciliationComparison(UUIDModel):
    RESULT_MATCHED = 'matched'
    RESULT_BRANCH_MISMATCH = 'branch_mismatch'
    RESULT_ORDER_ONLY = 'order_only'
    RESULT_SYSTEM_ONLY = 'system_only'
    RESULT_SYSTEM_DUPLICATE = 'system_duplicate'
    RESULT_SYSTEM_MISSING_SERIAL = 'system_missing_serial'
    RESULT_CHOICES = [
        (RESULT_MATCHED, '匹配'), (RESULT_BRANCH_MISMATCH, '分公司不一致'),
        (RESULT_ORDER_ONLY, '仅订单有'), (RESULT_SYSTEM_ONLY, '仅系统有'),
        (RESULT_SYSTEM_DUPLICATE, '系统序列号重复'),
        (RESULT_SYSTEM_MISSING_SERIAL, '系统缺少序列号'),
    ]

    version = models.ForeignKey(ReconciliationUploadVersion, on_delete=models.PROTECT, related_name='comparisons')
    result_type = models.CharField(max_length=32, choices=RESULT_CHOICES, db_index=True)
    order_row = models.ForeignKey(
        ReconciliationOrderRow, on_delete=models.PROTECT, null=True, blank=True,
        related_name='comparisons',
    )
    issue = models.ForeignKey(
        ReconciliationIssue, on_delete=models.PROTECT, null=True, blank=True,
        related_name='occurrences',
    )
    system_instance_id = models.UUIDField(null=True, blank=True)
    internal_code = models.CharField(max_length=100, blank=True, default='')
    system_serial_original = models.CharField(max_length=200, blank=True, default='')
    system_branch_id = models.UUIDField(null=True, blank=True)
    system_branch_name = models.CharField(max_length=100, blank=True, default='')
    system_status = models.CharField(max_length=20, blank=True, default='')
    item_code = models.CharField(max_length=100, blank=True, default='')
    item_name = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'reconciliation_comparison'
        ordering = ['order_row__row_number', 'internal_code']


class ReconciliationIssueHistory(UUIDModel):
    issue = models.ForeignKey(ReconciliationIssue, on_delete=models.PROTECT, related_name='history')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    old_status = models.CharField(max_length=20, blank=True, default='')
    new_status = models.CharField(max_length=20)
    old_conclusion = models.CharField(max_length=100, blank=True, default='')
    new_conclusion = models.CharField(max_length=100, blank=True, default='')
    old_note = models.TextField(blank=True, default='')
    new_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reconciliation_issue_history'
        ordering = ['-created_at']
