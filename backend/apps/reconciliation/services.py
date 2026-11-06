import calendar
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO

from django.db import transaction
from django.db.models import Case, CharField, Count, F, Q, Sum, Value, When
from django.db.models.functions import Trim, Upper
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.exceptions import ValidationError

from apps.assets.models import FixedAsset
from apps.organizations.models import Branch
from apps.reconciliation.models import (
    ReconciliationComparison,
    ReconciliationIssue,
    ReconciliationIssueHistory,
    ReconciliationOrderRow,
    ReconciliationTask,
    ReconciliationUploadVersion,
)
from apps.suppliers.models import Supplier


ITEM_CODES = ('A-a00001', 'A-a00008', 'A-a00011', 'A-a00012')
HEADERS = ('订单号', '序列号', '分公司', '起租日期', '记账日期', '月租金')
CENT = Decimal('0.01')


def _comparison_queryset_for_scope(queryset, scope):
    if scope.all:
        return queryset
    if not scope.branches:
        return queryset.none()

    branches = scope.branches
    has_visible_branch = Q(order_row__branch_id__in=branches) | Q(system_branch_id__in=branches)
    has_hidden_branch = (
        Q(order_row__branch_id__isnull=False) & ~Q(order_row__branch_id__in=branches)
    ) | (
        Q(system_branch_id__isnull=False) & ~Q(system_branch_id__in=branches)
    )
    return queryset.filter(has_visible_branch).exclude(has_hidden_branch)


def normalize_serial(value):
    return str(value or '').strip().upper()


def _branch_key(value):
    return re.sub(r'\s+', '', str(value or ''))


def _parse_date(value, row_number, field, errors):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        errors.append({'row': row_number, 'field': field, 'value': text, 'message': '日期格式必须为 YYYY-MM-DD'})
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        errors.append({'row': row_number, 'field': field, 'value': text, 'message': '日期无效'})
        return None


def _parse_money(value, row_number, field, errors, required=True):
    if value in (None, ''):
        if required:
            errors.append({'row': row_number, 'field': field, 'value': '', 'message': '金额不能为空'})
        return None
    try:
        amount = Decimal(str(value).strip())
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
            raise InvalidOperation
        return amount.quantize(CENT)
    except (InvalidOperation, ValueError):
        errors.append({'row': row_number, 'field': field, 'value': str(value), 'message': '金额须为非负且精确到分的数字'})
        return None


def billing_for_period(period, accounting_date, monthly_rent):
    days_in_month = calendar.monthrange(period.year, period.month)[1]
    month_start = period.replace(day=1)
    month_end = period.replace(day=days_in_month)
    if accounting_date > month_end:
        billing_days = 0
    else:
        billing_days = (month_end - max(accounting_date, month_start)).days + 1
    amount = (monthly_rent * Decimal(billing_days) / Decimal(days_in_month)).quantize(
        CENT, rounding=ROUND_HALF_UP,
    )
    return billing_days, amount


def parse_workbook(upload, period):
    """Parse and validate the entire agreed workbook before any task writes."""
    try:
        workbook = load_workbook(upload, read_only=True, data_only=True)
    except Exception as exc:
        raise ValidationError({'detail': '无法读取 Excel 文件，请确认上传的是有效的 .xlsx 文件'}) from exc

    sheet = workbook.active
    header_values = tuple(str(value or '').strip() for value in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ()))
    if header_values != HEADERS:
        raise ValidationError({
            'detail': '订单模板列名或顺序不正确',
            'expectedHeaders': list(HEADERS),
            'actualHeaders': list(header_values),
        })

    branches = list(Branch.objects.all().only('id', 'name'))
    branch_map = {}
    for branch in branches:
        branch_map.setdefault(_branch_key(branch.name), []).append(branch)

    errors = []
    parsed = []
    seen_serials = {}
    for row_number, values in enumerate(sheet.iter_rows(min_row=2, max_col=len(HEADERS), values_only=True), start=2):
        if not any(value not in (None, '') for value in values):
            continue
        values = tuple(values) + (None,) * (len(HEADERS) - len(values))
        order_no, serial, branch_text, start_raw, accounting_raw, rent_raw = values[:6]
        serial_original = str(serial or '').strip()
        serial_normalized = normalize_serial(serial_original)
        if not serial_normalized:
            errors.append({'row': row_number, 'field': '序列号', 'value': '', 'message': '序列号不能为空'})
        elif serial_normalized in seen_serials:
            errors.append({'row': row_number, 'field': '序列号', 'value': serial_original,
                           'message': f'序列号重复，首次出现在第 {seen_serials[serial_normalized]} 行'})
        else:
            seen_serials[serial_normalized] = row_number

        branch_original = str(branch_text or '').strip()
        matches = branch_map.get(_branch_key(branch_original), [])
        if len(matches) != 1:
            message = '分公司名称不能为空' if not branch_original else '分公司名称未匹配或对应多个系统分公司'
            errors.append({'row': row_number, 'field': '分公司', 'value': branch_original, 'message': message})

        lease_start = _parse_date(start_raw, row_number, '起租日期', errors)
        accounting = _parse_date(accounting_raw, row_number, '记账日期', errors)
        rent = _parse_money(rent_raw, row_number, '月租金', errors)
        if lease_start and accounting and lease_start > accounting:
            errors.append({'row': row_number, 'field': '记账日期', 'value': accounting.isoformat(), 'message': '记账日期不能早于起租日期'})
        if lease_start and accounting and rent is not None and len(matches) == 1 and serial_normalized:
            days, amount = billing_for_period(period, accounting, rent)
            parsed.append({
                'row_number': row_number,
                'order_number': str(order_no or '').strip(),
                'serial_original': serial_original,
                'serial_normalized': serial_normalized,
                'supplier_branch_text': branch_original,
                'branch': matches[0],
                'lease_start_date': lease_start,
                'accounting_date': accounting,
                'billing_days': days,
                'monthly_rent': rent,
                'month_amount': amount,
                'uploaded_billing_days': None,
                'uploaded_month_amount': None,
            })

    workbook.close()
    if errors:
        raise ValidationError({'detail': '订单校验失败，整份文件未导入', 'errors': errors})
    if not parsed:
        raise ValidationError({'detail': '订单中没有可导入的数据行'})
    return parsed


def _prepare_reconciliation_order(supplier_id, period, upload):
    try:
        period_date = date.fromisoformat(f'{period}-01')
    except (TypeError, ValueError):
        raise ValidationError({'period': '月份格式必须为 YYYY-MM'})
    supplier = Supplier.objects.filter(pk=supplier_id).first()
    if supplier is None:
        raise ValidationError({'supplier': '供应商不存在'})
    return supplier, period_date, parse_workbook(upload, period_date)


def preview_reconciliation_order(supplier_id, period, upload, user=None):
    """Validate and summarize an order workbook without persisting reconciliation data."""
    supplier, period_date, parsed = _prepare_reconciliation_order(supplier_id, period, upload)
    if user is not None:
        from core.permissions import validate_branches_in_scope
        validate_branches_in_scope(user, *(row['branch'] for row in parsed))
    branch_totals = {}
    order_keys = set()
    warnings = []
    total_amount = Decimal('0.00')
    for row in parsed:
        branch_id = str(row['branch'].pk)
        bucket = branch_totals.setdefault(branch_id, {
            'branch_id': branch_id, 'branch_name': row['branch'].name,
            'row_count': 0, 'month_amount': Decimal('0.00'),
        })
        bucket['row_count'] += 1
        bucket['month_amount'] += row['month_amount']
        order_keys.add((branch_id, row['order_number']))
        total_amount += row['month_amount']
    return {
        'supplier_id': str(supplier.pk), 'supplier_name': supplier.name,
        'period': period_date.strftime('%Y-%m'),
        'branch_count': len(branch_totals), 'order_count': len(order_keys),
        'row_count': len(parsed),
        'total_amount': str(total_amount.quantize(CENT)),
        'branch_totals': [
            {**bucket, 'month_amount': str(bucket['month_amount'].quantize(CENT))}
            for bucket in branch_totals.values()
        ],
        'calculation_warnings': warnings,
    }


def _issue_key(supplier_id, issue_type, serial, discriminator=''):
    raw = f'{supplier_id}|{issue_type}|{serial}|{discriminator}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _issue_for(task, issue_type, serial, discriminator='', cache=None):
    issue_key = _issue_key(task.supplier_id, issue_type, serial, discriminator)
    if cache is not None and issue_key in cache:
        return cache[issue_key]
    issue, created = ReconciliationIssue.objects.get_or_create(
        issue_key=issue_key,
        defaults={
            'supplier': task.supplier, 'issue_type': issue_type,
            'serial_normalized': serial, 'first_period': task.period,
            'last_period': task.period,
        },
    )
    if not created:
        old_status = issue.status
        issue.last_period = max(issue.last_period, task.period)
        issue.status = ReconciliationIssue.STATUS_OPEN
        issue.save(update_fields=['last_period', 'status', 'updated_at'])
        if old_status != issue.status:
            ReconciliationIssueHistory.objects.create(
                issue=issue, user=task.created_by, user_name=task.created_by_name,
                old_status=old_status,
                new_status=issue.status, old_conclusion=issue.conclusion,
                new_conclusion=issue.conclusion, old_note=issue.note, new_note=issue.note,
            )
    if cache is not None:
        cache[issue_key] = issue
    return issue


def _snapshot_system(instance):
    return {
        'system_instance_id': instance.pk,
        'internal_code': instance.内部编号,
        'system_serial_original': instance.序列号,
        'system_branch_id': instance.branch_id,
        'system_branch_name': instance.branch.name if instance.branch_id else '',
        'system_status': instance.当前状态,
        'item_code': instance.item.asset_code,
        'item_name': instance.item.asset_name,
    }


def _create_comparison(version, result_type, order_row=None, instance=None, issue=None):
    values = {'version': version, 'result_type': result_type, 'order_row': order_row, 'issue': issue}
    if instance is not None:
        values.update(_snapshot_system(instance))
    return ReconciliationComparison(**values)


def _supplier_scope(task):
    name = task.supplier.name
    return (
        Q(供应商=name)
        | (Q(供应商='') & Q(birth_line__供应商=name))
        | (
            Q(供应商='')
            & Q(birth_line__供应商='')
            & Q(birth_line__transfer__供应商=name)
        )
    )


def _effective_supplier_expression():
    return Case(
        When(~Q(供应商=''), then=F('供应商')),
        When(~Q(birth_line__供应商=''), then=F('birth_line__供应商')),
        When(~Q(birth_line__transfer__供应商=''), then=F('birth_line__transfer__供应商')),
        default=Value(''),
        output_field=CharField(),
    )


def _prefetch_issues(task, specs):
    """Create/reuse all issue rows needed by a comparison in bounded queries."""
    unique_specs = {}
    for issue_type, serial, discriminator in specs:
        key = _issue_key(task.supplier_id, issue_type, serial, discriminator)
        unique_specs[key] = (issue_type, serial)
    if not unique_specs:
        return {}

    entries = list(unique_specs.items())
    existing = {}
    for offset in range(0, len(entries), 500):
        batch = dict(entries[offset:offset + 500])
        current = {
            issue.issue_key: issue
            for issue in ReconciliationIssue.objects.filter(issue_key__in=batch)
        }
        missing = [
            ReconciliationIssue(
                issue_key=key,
                supplier_id=task.supplier_id,
                issue_type=issue_type,
                serial_normalized=serial,
                first_period=task.period,
                last_period=task.period,
            )
            for key, (issue_type, serial) in batch.items()
            if key not in current
        ]
        if missing:
            ReconciliationIssue.objects.bulk_create(missing, batch_size=500, ignore_conflicts=True)
            current.update({
                issue.issue_key: issue
                for issue in ReconciliationIssue.objects.filter(issue_key__in=batch)
            })
        existing.update(current)
    changed = []
    histories = []
    changed_at = timezone.now()
    for issue in existing.values():
        old_status = issue.status
        old_last_period = issue.last_period
        issue.last_period = max(issue.last_period, task.period)
        issue.status = ReconciliationIssue.STATUS_OPEN
        if issue.last_period != old_last_period or old_status != issue.status:
            issue.updated_at = changed_at
            changed.append(issue)
        if old_status != issue.status:
            histories.append(ReconciliationIssueHistory(
                issue=issue, user=task.created_by, user_name=task.created_by_name,
                old_status=old_status,
                new_status=issue.status, old_conclusion=issue.conclusion,
                new_conclusion=issue.conclusion, old_note=issue.note, new_note=issue.note,
            ))
    if changed:
        ReconciliationIssue.objects.bulk_update(changed, ['last_period', 'status', 'updated_at'], batch_size=500)
    if histories:
        ReconciliationIssueHistory.objects.bulk_create(histories, batch_size=500)
    return existing


def build_comparison(task, version):
    order_rows = list(version.order_rows.select_related('branch').all())
    order_by_serial = {row.serial_normalized: row for row in order_rows}
    eligible = FixedAsset.objects.filter(
        item__asset_code__in=ITEM_CODES,
        当前状态__in=[FixedAsset.STATUS_IN_USE, FixedAsset.STATUS_IN_STOCK],
    )
    instances = list(
        eligible.filter(_supplier_scope(task)).select_related(
            'item', 'branch', 'birth_line__transfer',
        ).order_by('内部编号')
    )
    excluded = eligible.exclude(_supplier_scope(task))
    excluded_count = excluded.count()
    known_supplier_names = set(Supplier.objects.values_list('name', flat=True))
    supplier_counts = eligible.annotate(
        effective_supplier=_effective_supplier_expression(),
    ).values('effective_supplier').annotate(total=Count('pk'))
    unknown_supplier_count = sum(
        row['total'] for row in supplier_counts
        if row['effective_supplier'] not in known_supplier_names
    )
    diagnostic_serials = set(order_by_serial)
    excluded_by_serial = {}
    excluded_unknown_serials = set()
    if diagnostic_serials:
        # Diagnostics only inspect serials present in the upload. Unrelated assets
        # remain in the database and do not scale the import's Python workload.
        serial_values = list(diagnostic_serials)
        for offset in range(0, len(serial_values), 500):
            diagnostic_rows = eligible.annotate(
                normalized_serial=Upper(Trim(F('序列号'))),
            ).filter(normalized_serial__in=serial_values[offset:offset + 500]).values(
                '序列号', '供应商', 'birth_line__供应商', 'birth_line__transfer__供应商',
            )
            for row in diagnostic_rows.iterator(chunk_size=500):
                serial = normalize_serial(row['序列号'])
                if not serial:
                    continue
                supplier = (
                    row['供应商']
                    or row['birth_line__供应商']
                    or row['birth_line__transfer__供应商']
                    or ''
                )
                excluded_by_serial.setdefault(serial, set()).add(supplier)
                if supplier not in known_supplier_names:
                    excluded_unknown_serials.add(serial)
    foreign_serials = sorted(
        serial for serial, suppliers in excluded_by_serial.items()
        if any(value in known_supplier_names and value != task.supplier.name for value in suppliers)
    )
    unknown_serials = sorted(excluded_unknown_serials)
    scope_diagnostics = {
        'excluded_count': excluded_count,
        'unknown_supplier_count': unknown_supplier_count,
        'unknown_supplier_serials': unknown_serials[:100],
        'unknown_supplier_serial_count': len(unknown_serials),
        'foreign_supplier_serials': foreign_serials[:100],
        'foreign_supplier_serial_count': len(foreign_serials),
    }
    with_serial = {}
    missing_serial = []
    for instance in instances:
        serial = normalize_serial(instance.序列号)
        if not serial:
            missing_serial.append(instance)
        else:
            with_serial.setdefault(serial, []).append(instance)

    seen_issue_ids = set()
    comparison_rows = []
    duplicate_serials = {serial for serial, group in with_serial.items() if len(group) > 1}
    issue_specs = [
        (ReconciliationComparison.RESULT_SYSTEM_DUPLICATE, serial, '')
        for serial in duplicate_serials
    ]
    issue_specs.extend(
        (ReconciliationComparison.RESULT_ORDER_ONLY, serial, '')
        for serial, order_row in order_by_serial.items()
        if serial not in duplicate_serials and serial not in with_serial
    )
    issue_specs.extend(
        (ReconciliationComparison.RESULT_BRANCH_MISMATCH, serial, '')
        for serial, order_row in order_by_serial.items()
        if serial not in duplicate_serials
        and serial in with_serial
        and with_serial[serial][0].branch_id != order_row.branch_id
    )
    issue_specs.extend(
        (ReconciliationComparison.RESULT_SYSTEM_ONLY, serial, '')
        for serial in with_serial
        if serial not in duplicate_serials and serial not in order_by_serial
    )
    issue_specs.extend(
        (ReconciliationComparison.RESULT_SYSTEM_MISSING_SERIAL, '', str(instance.pk))
        for instance in missing_serial
    )
    issue_cache = _prefetch_issues(task, issue_specs)
    for serial in duplicate_serials:
        issue = _issue_for(task, ReconciliationComparison.RESULT_SYSTEM_DUPLICATE, serial, cache=issue_cache)
        seen_issue_ids.add(issue.pk)
        order_row = order_by_serial.get(serial)
        for instance in with_serial[serial]:
            comparison_rows.append(_create_comparison(version, ReconciliationComparison.RESULT_SYSTEM_DUPLICATE, order_row, instance, issue))

    for serial, order_row in order_by_serial.items():
        if serial in duplicate_serials:
            continue
        group = with_serial.get(serial, [])
        if not group:
            issue = _issue_for(task, ReconciliationComparison.RESULT_ORDER_ONLY, serial, cache=issue_cache)
            seen_issue_ids.add(issue.pk)
            comparison_rows.append(_create_comparison(version, ReconciliationComparison.RESULT_ORDER_ONLY, order_row, issue=issue))
            continue
        instance = group[0]
        if instance.branch_id != order_row.branch_id:
            issue = _issue_for(task, ReconciliationComparison.RESULT_BRANCH_MISMATCH, serial, cache=issue_cache)
            seen_issue_ids.add(issue.pk)
            comparison_rows.append(_create_comparison(version, ReconciliationComparison.RESULT_BRANCH_MISMATCH, order_row, instance, issue))
        else:
            comparison_rows.append(_create_comparison(version, ReconciliationComparison.RESULT_MATCHED, order_row, instance))

    for serial, group in with_serial.items():
        if serial in duplicate_serials:
            continue
        if serial in order_by_serial:
            continue
        issue = _issue_for(task, ReconciliationComparison.RESULT_SYSTEM_ONLY, serial, cache=issue_cache)
        seen_issue_ids.add(issue.pk)
        for instance in group:
            comparison_rows.append(_create_comparison(version, ReconciliationComparison.RESULT_SYSTEM_ONLY, instance=instance, issue=issue))

    for instance in missing_serial:
        issue = _issue_for(
            task, ReconciliationComparison.RESULT_SYSTEM_MISSING_SERIAL, '', str(instance.pk), cache=issue_cache,
        )
        seen_issue_ids.add(issue.pk)
        comparison_rows.append(_create_comparison(version, ReconciliationComparison.RESULT_SYSTEM_MISSING_SERIAL, instance=instance, issue=issue))

    ReconciliationComparison.objects.bulk_create(comparison_rows, batch_size=500)

    previous_issues = list(ReconciliationIssue.objects.filter(
        supplier=task.supplier,
        status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
    ).filter(
        Q(last_period__lt=task.period) | Q(occurrences__version__task=task),
    ).exclude(pk__in=seen_issue_ids).distinct())
    recurring_issues = [
        issue for issue in previous_issues
        if issue.status != ReconciliationIssue.STATUS_NOT_RECURRED
    ]
    changed_at = timezone.now()
    for issue in recurring_issues:
        issue.status = ReconciliationIssue.STATUS_NOT_RECURRED
        issue.updated_at = changed_at
    if recurring_issues:
        ReconciliationIssue.objects.bulk_update(recurring_issues, ['status', 'updated_at'], batch_size=500)
        ReconciliationIssueHistory.objects.bulk_create([
            ReconciliationIssueHistory(
                issue=issue, user=task.created_by, user_name=task.created_by_name,
                old_status=ReconciliationIssue.STATUS_OPEN,
                new_status=ReconciliationIssue.STATUS_NOT_RECURRED,
                old_conclusion=issue.conclusion, new_conclusion=issue.conclusion,
                old_note=issue.note, new_note=issue.note,
            )
            for issue in recurring_issues
        ], batch_size=500)
    return scope_diagnostics


@transaction.atomic
def import_reconciliation_order(supplier_id, period, upload, user):
    # Parse before mutating task state so a bad replacement leaves the active version intact.
    supplier, period_date, parsed = _prepare_reconciliation_order(supplier_id, period, upload)
    from core.permissions import validate_branches_in_scope
    validate_branches_in_scope(user, *(row['branch'] for row in parsed))
    upload.seek(0)
    task = ReconciliationTask.objects.select_for_update().filter(
        supplier=supplier, period=period_date,
    ).first()
    if task and task.current_version_id:
        existing_comparisons = ReconciliationComparison.objects.filter(version_id=task.current_version_id)
        has_unassigned_comparison = existing_comparisons.filter(
            order_row__isnull=True, system_branch_id__isnull=True,
        ).exists()
        if has_unassigned_comparison:
            from apps.permissions.scope import resolve_user_scope
            if not resolve_user_scope(user).all:
                raise ValidationError({'detail': '已有对账版本包含无法确定分公司范围的记录，不能由当前账号替换'})
        existing_branch_ids = set(existing_comparisons.values_list('order_row__branch_id', flat=True))
        existing_branch_ids.update(existing_comparisons.values_list('system_branch_id', flat=True))
        validate_branches_in_scope(user, *(branch_id for branch_id in existing_branch_ids if branch_id))
    if task and task.status == ReconciliationTask.STATUS_ARCHIVED:
        raise ValidationError({'detail': '该供应商月份任务已归档，不能覆盖'})
    if task is None:
        task = ReconciliationTask.objects.create(
            supplier=supplier, period=period_date, created_by=user,
            created_by_name=user.name,
        )

    version_number = (task.versions.order_by('-version_number').values_list('version_number', flat=True).first() or 0) + 1
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=version_number, file=upload,
        uploaded_by=user, uploaded_by_name=user.name, row_count=len(parsed),
        calculation_warnings=[],
    )
    rows = [ReconciliationOrderRow(version=version, **entry) for entry in parsed]
    ReconciliationOrderRow.objects.bulk_create(rows)
    version.refresh_from_db()

    # Compare against current system facts while keeping every accepted version immutable.
    scope_diagnostics = build_comparison(task, version)
    version.summary = build_version_summary(task, version, scope_diagnostics)
    version.save(update_fields=['summary'])
    task.current_version = version
    task.save(update_fields=['current_version', 'updated_at'])
    return task, version


@transaction.atomic
def rematch_task(task, user):
    """Re-run comparison for a task using the current version's order rows,
    without re-uploading the Excel file. Returns the new version number."""
    task = ReconciliationTask.objects.select_for_update().get(pk=task.pk)
    if task.status == ReconciliationTask.STATUS_ARCHIVED:
        raise ValidationError({'detail': '该供应商月份任务已归档，不能重新对账'})
    old_version = task.current_version
    if old_version is None:
        raise ValidationError({'detail': '当前任务无可用版本，无法重新对账'})

    version_number = (
        task.versions.order_by('-version_number').values_list('version_number', flat=True).first() or 0
    ) + 1
    new_version = ReconciliationUploadVersion.objects.create(
        task=task,
        version_number=version_number,
        file=old_version.file.name,
        uploaded_by=user,
        uploaded_by_name=user.name,
        row_count=old_version.row_count,
        calculation_warnings=old_version.calculation_warnings,
    )

    old_rows = list(old_version.order_rows.select_related('branch').all())
    new_rows = [
        ReconciliationOrderRow(
            version=new_version,
            row_number=row.row_number,
            order_number=row.order_number,
            serial_original=row.serial_original,
            serial_normalized=row.serial_normalized,
            supplier_branch_text=row.supplier_branch_text,
            branch_id=row.branch_id,
            lease_start_date=row.lease_start_date,
            accounting_date=row.accounting_date,
            billing_days=row.billing_days,
            monthly_rent=row.monthly_rent,
            month_amount=row.month_amount,
            uploaded_billing_days=row.uploaded_billing_days,
            uploaded_month_amount=row.uploaded_month_amount,
        )
        for row in old_rows
    ]
    ReconciliationOrderRow.objects.bulk_create(new_rows)

    scope_diagnostics = build_comparison(task, new_version)
    new_version.summary = build_version_summary(task, new_version, scope_diagnostics)
    new_version.save(update_fields=['summary'])

    task.current_version = new_version
    task.save(update_fields=['current_version', 'updated_at'])

    return version_number


def update_issue(issue, user, status=None, conclusion=None, note=None, conclusion_type=None):
    old = {'status': issue.status, 'conclusion': issue.conclusion, 'note': issue.note}
    if status is not None:
        if status not in (ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_CLOSED):
            raise ValidationError({'status': '状态只允许待处理或结案'})
        if status == ReconciliationIssue.STATUS_CLOSED and issue.status == ReconciliationIssue.STATUS_NOT_RECURRED:
            pass
        issue.status = status
        issue.closed_by = user if status == ReconciliationIssue.STATUS_CLOSED else None
        issue.closed_by_name = user.name if status == ReconciliationIssue.STATUS_CLOSED else ''
        issue.closed_at = timezone.now() if status == ReconciliationIssue.STATUS_CLOSED else None
    if conclusion is not None:
        issue.conclusion = conclusion.strip()
    if note is not None:
        issue.note = note.strip()
    if conclusion_type is not None:
        valid_values = {v for v, _ in ReconciliationIssue.CONCLUSION_CHOICES}
        valid_values.add('')
        if conclusion_type not in valid_values:
            raise ValidationError({'conclusion_type': '无效的结论类型'})
        issue.conclusion_type = conclusion_type
    issue.handled_by = user
    issue.handled_by_name = user.name
    issue.handled_at = timezone.now()
    issue.save()
    ReconciliationIssueHistory.objects.create(
        issue=issue, user=user, user_name=user.name,
        old_status=old['status'], new_status=issue.status,
        old_conclusion=old['conclusion'], new_conclusion=issue.conclusion,
        old_note=old['note'], new_note=issue.note,
    )
    return issue


def build_version_summary(task, version, scope_diagnostics=None):
    counts = dict(
        ReconciliationComparison.objects.filter(version=version)
        .values('result_type').annotate(n=Count('id'))
        .values_list('result_type', 'n')
    )
    pending_count = ReconciliationComparison.objects.filter(
        version=version,
    ).exclude(result_type=ReconciliationComparison.RESULT_MATCHED).filter(
        issue__status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
        issue__conclusion='',
    ).count()
    branch_totals = {}
    for bucket in version.order_rows.values('branch_id', 'branch__name').annotate(
        row_count=Count('pk'), monthly_rent=Sum('monthly_rent'), month_amount=Sum('month_amount'),
    ):
        branch_totals[str(bucket['branch_id'])] = {
            'branch_id': str(bucket['branch_id']),
            'branch_name': bucket['branch__name'],
            'row_count': bucket['row_count'],
            'monthly_rent': str((bucket['monthly_rent'] or Decimal('0.00')).quantize(CENT)),
            'month_amount': str((bucket['month_amount'] or Decimal('0.00')).quantize(CENT)),
        }
    total = version.order_rows.aggregate(total=Sum('month_amount'))['total'] or Decimal('0.00')
    return {
        'row_count': version.row_count,
        'counts': counts,
        'pending_count': pending_count,
        'total_amount': str(total.quantize(CENT)),
        'branch_totals': list(branch_totals.values()),
        'comparison_count': sum(counts.values()),
        'scope_diagnostics': scope_diagnostics or {},
    }


def task_summary(task, pending_count=None):
    version = task.current_version
    if version is None:
        return {
            'row_count': 0, 'counts': {}, 'pending_count': 0,
            'total_amount': '0.00', 'branch_totals': [],
            'comparison_count': 0, 'scope_diagnostics': {},
        }
    if version.summary:
        summary = dict(version.summary)
        # Issue conclusions can change after import; refresh this small aggregate
        # without re-reading order rows or comparison payloads.
        if pending_count is None:
            pending_count = ReconciliationComparison.objects.filter(
                version=version,
            ).exclude(result_type=ReconciliationComparison.RESULT_MATCHED).filter(
                issue__status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
                issue__conclusion='',
            ).count()
        summary['pending_count'] = pending_count
        return summary
    return build_version_summary(task, version)


def build_payment_summary(task, scope):
    """聚合付款明细：confirmed/pending 金额及明细行列表。"""
    version = task.current_version
    if version is None:
        return {
            'confirmed_amount': '0.00',
            'pending_amount': '0.00',
            'total_amount': '0.00',
            'can_archive': True,
            'rows': [],
        }

    comparisons = _comparison_queryset_for_scope(
        version.comparisons.all(), scope,
    ).select_related('order_row__branch', 'issue')

    confirmed = Decimal('0.00')
    pending = Decimal('0.00')
    rows = []

    month_end_day = calendar.monthrange(task.period.year, task.period.month)[1]
    month_end = task.period.replace(day=month_end_day)

    for comp in comparisons:
        order = comp.order_row
        if order is None:
            # system_only rows have no order_row — skip for payment amounts
            # but still include in rows (no billing amount)
            branch_name = comp.system_branch_name if comp.system_branch_id is not None else ''
            rows.append({
                'serial': comp.system_serial_original,
                'branch': branch_name,
                'internal_code': comp.internal_code,
                'lease_start_date': None,
                'accounting_date': None,
                'billing_days': None,
                'monthly_rent': None,
                'month_amount': None,
                'billing_status': None,
                'conclusion_type': comp.issue.conclusion_type if comp.issue_id else '',
            })
            continue

        amount = order.month_amount or Decimal('0.00')

        if comp.result_type == ReconciliationComparison.RESULT_MATCHED:
            confirmed += amount
        else:
            # diff row
            issue = comp.issue
            if issue is not None and issue.conclusion_type != '':
                confirmed += amount
            elif (
                issue is not None
                and issue.conclusion_type == ''
                and issue.status in (ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED)
            ):
                pending += amount

        # determine branch: order_row branch takes priority
        branch_name = order.branch.name if order.branch_id else comp.system_branch_name

        future_billing = order.accounting_date > month_end
        billing_status = 'not_started' if future_billing else 'billable'

        rows.append({
            'serial': order.serial_original,
            'branch': branch_name,
            'internal_code': comp.internal_code,
            'lease_start_date': order.lease_start_date.isoformat(),
            'accounting_date': order.accounting_date.isoformat(),
            'billing_days': order.billing_days,
            'monthly_rent': str(order.monthly_rent),
            'month_amount': str(order.month_amount),
            'billing_status': billing_status,
            'conclusion_type': comp.issue.conclusion_type if comp.issue_id else '',
        })

    confirmed = confirmed.quantize(CENT, rounding=ROUND_HALF_UP)
    pending = pending.quantize(CENT, rounding=ROUND_HALF_UP)
    total = (confirmed + pending).quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        'confirmed_amount': str(confirmed),
        'pending_amount': str(pending),
        'total_amount': str(total),
        'can_archive': pending == Decimal('0.00'),
        'rows': rows,
    }


def build_branch_summary(task, scope):
    """按分公司聚合对账差异状态，返回列表供 branch-summary 接口使用。"""
    version = task.current_version
    if version is None:
        return []

    comparisons = _comparison_queryset_for_scope(
        version.comparisons.all(), scope,
    ).select_related('order_row__branch', 'issue')

    buckets = {}
    for comp in comparisons:
        if comp.order_row_id is not None:
            branch_id = str(comp.order_row.branch_id)
            branch_name = comp.order_row.branch.name
        elif comp.system_branch_id is not None:
            branch_id = str(comp.system_branch_id)
            branch_name = comp.system_branch_name
        else:
            continue

        if branch_id not in buckets:
            buckets[branch_id] = {
                'branch_id': branch_id,
                'branch_name': branch_name,
                'order_count': 0,
                'matched_count': 0,
                'diff_count': 0,
                'pending_count': 0,
                'month_amount': Decimal('0.00'),
            }

        bucket = buckets[branch_id]
        bucket['order_count'] += 1

        if comp.result_type == ReconciliationComparison.RESULT_MATCHED:
            bucket['matched_count'] += 1
            if comp.order_row.month_amount is not None:
                bucket['month_amount'] += comp.order_row.month_amount
        else:
            bucket['diff_count'] += 1
            if (
                comp.issue_id is not None
                and comp.issue.conclusion_type == ''
                and comp.issue.status in (
                    ReconciliationIssue.STATUS_OPEN,
                    ReconciliationIssue.STATUS_NOT_RECURRED,
                )
            ):
                bucket['pending_count'] += 1

    result = sorted(buckets.values(), key=lambda b: b['branch_name'])
    return [
        {**b, 'month_amount': str(b['month_amount'].quantize(CENT))}
        for b in result
    ]
