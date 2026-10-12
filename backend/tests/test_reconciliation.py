from datetime import date
from decimal import Decimal
from io import BytesIO
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from openpyxl import Workbook
from rest_framework.exceptions import ValidationError

from apps.assets.models import FixedAsset
from apps.categories.models import Category
from apps.reconciliation.models import ReconciliationComparison, ReconciliationIssue, ReconciliationTask, ReconciliationUploadVersion
from apps.reconciliation.services import (
    billing_for_period,
    import_reconciliation_order,
    normalize_serial,
    parse_workbook,
    preview_reconciliation_order,
)
from apps.suppliers.models import Supplier


def _workbook(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['订单号', '序列号', '分公司', '起租日期', '记账日期', '记账天数', '月租金', '本月金额'])
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def _upload(rows, name='order.xlsx'):
    return SimpleUploadedFile(name, _workbook(rows).getvalue())


@pytest.mark.parametrize(('period', 'accounting', 'rent', 'days', 'amount'), [
    (date(2026, 2, 1), date(2026, 1, 15), Decimal('100.00'), 28, Decimal('100.00')),
    (date(2024, 2, 1), date(2024, 2, 15), Decimal('100.00'), 15, Decimal('51.72')),
    (date(2026, 4, 1), date(2026, 4, 30), Decimal('100.00'), 1, Decimal('3.33')),
    (date(2026, 4, 1), date(2026, 5, 1), Decimal('100.00'), 0, Decimal('0.00')),
])
def test_billing_uses_calendar_days_and_cent_rounding(period, accounting, rent, days, amount):
    assert billing_for_period(period, accounting, rent) == (days, amount)


def test_serial_normalization_trims_and_uppercases():
    assert normalize_serial('  ab-012x  ') == 'AB-012X'


def test_import_rejects_entire_workbook_on_duplicate_serial(branch):
    rows = [
        ['PO-1', 'sn-1', branch.name, '2026-09-01', '2026-09-01', None, '100.00', None],
        ['PO-1', ' SN-1 ', branch.name, '2026-09-01', '2026-09-02', None, '100.00', None],
    ]
    with pytest.raises(ValidationError) as exc:
        parse_workbook(_upload(rows), date(2026, 9, 1))
    assert str(exc.value.detail['errors'][0]['row']) == '3'
    assert '首次出现在第 2 行' in exc.value.detail['errors'][0]['message']


def test_import_rejects_entire_workbook_on_unknown_branch(branch):
    rows = [
        ['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-01', None, '100.00', None],
        ['PO-2', 'SN-2', '不存在的分公司', '2026-09-01', '2026-09-01', None, '100.00', None],
    ]
    with pytest.raises(ValidationError) as exc:
        parse_workbook(_upload(rows), date(2026, 9, 1))
    assert str(exc.value.detail['errors'][0]['row']) == '3'
    assert exc.value.detail['errors'][0]['value'] == '不存在的分公司'


@pytest.mark.django_db
def test_preview_returns_summary_and_calculation_warnings_without_writes(branch):
    supplier = Supplier.objects.create(name='预览租赁商')
    result = preview_reconciliation_order(
        supplier.pk, '2026-09', _upload([
            ['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-20', 0, '31.00', '0.00'],
            ['PO-2', 'SN-2', branch.name, '2026-09-01', '2026-09-01', 30, '20.00', '20.00'],
        ]),
    )
    assert result['branch_count'] == 1
    assert result['order_count'] == 2
    assert result['row_count'] == 2
    assert result['total_amount'] == '31.37'
    assert result['calculation_warnings'] == [{
        'row': 2, 'uploaded_billing_days': 0, 'calculated_billing_days': 11,
        'uploaded_month_amount': '0.00', 'calculated_month_amount': '11.37',
    }]
    assert ReconciliationTask.objects.count() == 0
    assert ReconciliationUploadVersion.objects.count() == 0
    assert ReconciliationComparison.objects.count() == 0


@pytest.mark.django_db
def test_preview_rejects_invalid_branch_entire_file_without_writes(branch, authenticated_client):
    supplier = Supplier.objects.create(name='预览校验租赁商')
    response = authenticated_client.post(
        '/api/reconciliation/tasks/preview',
        {
            'supplier': str(supplier.pk), 'period': '2026-09',
            'file': _upload([
                ['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-01', None, '10.00', None],
                ['PO-2', 'SN-2', '不存在的分公司', '2026-09-01', '2026-09-01', None, '10.00', None],
            ]),
        },
        format='multipart',
    )
    assert response.status_code == 400
    assert response.data['errors'][0]['row'] == '3'
    assert response.data['errors'][0]['field'] == '分公司'
    assert response.data['errors'][0]['value'] == '不存在的分公司'
    assert ReconciliationTask.objects.count() == 0
    assert ReconciliationUploadVersion.objects.count() == 0


@pytest.mark.django_db
def test_preview_api_enforces_admin_and_xlsx_extension(manager_client, authenticated_client, branch):
    supplier = Supplier.objects.create(name='预览权限租赁商')
    form = {
        'supplier': str(supplier.pk), 'period': '2026-09',
        'file': _upload([['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-01', None, '10.00', None]], 'order.csv'),
    }
    assert manager_client.post('/api/reconciliation/tasks/preview', form, format='multipart').status_code == 403
    response = authenticated_client.post('/api/reconciliation/tasks/preview', form, format='multipart')
    assert response.status_code == 400
    assert 'xlsx' in response.data['detail']


@pytest.mark.django_db
def test_upload_replacement_is_atomic_and_archived_task_cannot_be_overwritten(branch, admin_user, tmp_path):
    supplier = Supplier.objects.create(name='测试租赁商')
    item = Category.objects.create(
        asset_category='固定资产', item_category='电脑', asset_name='测试电脑',
        asset_code='A-a00008', unit='台', management_type='instance',
    )
    FixedAsset.objects.create(
        item=item, 内部编号='A-a00008-CS001-1', 序列号='SN-1', 当前状态='在用', branch=branch,
    )
    rows = [['PO-1', 'sn-1', branch.name, '2026-09-01', '2026-09-01', None, '100.00', None]]
    with override_settings(MEDIA_ROOT=tmp_path):
        task, version = import_reconciliation_order(supplier.pk, '2026-09', _upload(rows), admin_user)
        assert version.version_number == 1
        assert version.comparisons.get().result_type == ReconciliationComparison.RESULT_MATCHED

        bad_rows = [['PO-2', '', branch.name, '2026-09-01', '2026-09-01', None, '200.00', None]]
        with pytest.raises(ValidationError):
            import_reconciliation_order(supplier.pk, '2026-09', _upload(bad_rows), admin_user)
        task.refresh_from_db()
        assert task.current_version_id == version.pk
        assert ReconciliationUploadVersion.objects.filter(task=task).count() == 1

        replacement, version2 = import_reconciliation_order(supplier.pk, '2026-09', _upload([
            ['PO-2', 'SN-1', branch.name, '2026-09-01', '2026-09-16', None, '100.00', None],
        ]), admin_user)
        assert replacement.pk == task.pk
        assert version2.version_number == 2
        assert version2.order_rows.get().billing_days == 15
        assert version2.order_rows.get().month_amount == Decimal('50.00')

        task.status = ReconciliationTask.STATUS_ARCHIVED
        task.save(update_fields=['status'])
        with pytest.raises(ValidationError):
            import_reconciliation_order(supplier.pk, '2026-09', _upload(rows), admin_user)
        assert ReconciliationUploadVersion.objects.filter(task=task).count() == 2


@pytest.mark.django_db
def test_system_duplicate_serial_is_reported_even_without_order_match(branch, second_branch, admin_user, tmp_path):
    supplier = Supplier.objects.create(name='测试租赁商2')
    item = Category.objects.create(
        asset_category='固定资产', item_category='电脑', asset_name='测试电脑',
        asset_code='A-a00001', unit='台', management_type='instance',
    )
    for suffix, instance_branch in ((1, branch), (2, second_branch)):
        FixedAsset.objects.create(
            item=item, 内部编号=f'A-a00001-CS001-{suffix}', 序列号='DUP-1',
            当前状态='在用', branch=instance_branch,
        )
    with override_settings(MEDIA_ROOT=tmp_path):
        _, version = import_reconciliation_order(supplier.pk, '2026-09', _upload([
            ['PO-1', 'OTHER', branch.name, '2026-09-01', '2026-09-01', None, '10.00', None],
        ]), admin_user)
    assert version.comparisons.filter(result_type=ReconciliationComparison.RESULT_SYSTEM_DUPLICATE).count() == 2


@pytest.mark.django_db
def test_reconciliation_api_is_admin_only_and_imports_from_reconciliation_screen(
    authenticated_client, manager_client, branch, tmp_path,
):
    supplier = Supplier.objects.create(name='API测试租赁商')
    url = '/api/reconciliation/tasks'
    assert manager_client.get(url).status_code == 403
    assert authenticated_client.get(url).status_code == 200
    assert 'unresolved_summary' in authenticated_client.get(url).data

    with override_settings(MEDIA_ROOT=tmp_path):
        response = authenticated_client.post(
            '/api/reconciliation/tasks/import',
            {
                'supplier': str(supplier.pk), 'period': '2026-09',
                'file': _upload([[
                    'PO-API', 'API-SN', branch.name, '2026-09-01', '2026-09-20', 0,
                    '31.00', '0.00',
                ]]),
            },
            format='multipart',
        )
    assert response.status_code == 200, response.data
    payload = json.loads(response.rendered_content)
    assert payload['period'] == '2026-09'
    assert payload['totalAmount'] == '11.37'
    assert payload['currentVersion'] == 1


@pytest.mark.django_db
def test_task_list_unresolved_summary_groups_open_issues_and_excludes_closed(
    authenticated_client, branch,
):
    first_supplier = Supplier.objects.create(name='汇总供应商甲')
    second_supplier = Supplier.objects.create(name='汇总供应商乙')
    for supplier, key, period, issue_status in [
        (first_supplier, 'summary-1', '2026-07-01', ReconciliationIssue.STATUS_OPEN),
        (first_supplier, 'summary-2', '2026-07-01', ReconciliationIssue.STATUS_NOT_RECURRED),
        (first_supplier, 'summary-3', '2026-08-01', ReconciliationIssue.STATUS_OPEN),
        (second_supplier, 'summary-4', '2026-07-01', ReconciliationIssue.STATUS_CLOSED),
    ]:
        ReconciliationIssue.objects.create(
            supplier=supplier, issue_key=key, issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
            serial_normalized=key, first_period=period, last_period=period, status=issue_status,
        )

    response = authenticated_client.get('/api/reconciliation/tasks')

    assert response.status_code == 200
    assert response.data['unresolved_summary']['total_count'] == 3
    assert response.data['unresolved_summary']['groups'] == [
        {
            'supplier_id': str(first_supplier.pk), 'supplier_name': first_supplier.name,
            'first_period': '2026-08', 'count': 1,
        },
        {
            'supplier_id': str(first_supplier.pk), 'supplier_name': first_supplier.name,
            'first_period': '2026-07', 'count': 2,
        },
    ]
