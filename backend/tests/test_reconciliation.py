from datetime import date
from decimal import Decimal
from io import BytesIO
import json
from time import perf_counter

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import override_settings
from openpyxl import Workbook
from rest_framework.exceptions import ValidationError

from apps.assets.models import FixedAsset
from apps.categories.models import Category
from apps.reconciliation.models import (
    ReconciliationComparison,
    ReconciliationIssue,
    ReconciliationOrderRow,
    ReconciliationTask,
    ReconciliationUploadVersion,
)
from apps.reconciliation.services import (
    billing_for_period,
    import_reconciliation_order,
    normalize_serial,
    parse_workbook,
    preview_reconciliation_order,
)
from apps.suppliers.models import Supplier
from apps.transfers.models import Transfer, TransferLine
from apps.permissions.models import ManagementScope, OperationGrant
from apps.users.models import User
from conftest import _client_for


def _workbook(rows, headers=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers or ['订单号', '序列号', '分公司', '起租日期', '记账日期', '月租金'])
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def _upload(rows, name='order.xlsx', headers=None):
    return SimpleUploadedFile(name, _workbook(rows, headers=headers).getvalue())


def _reconciliation_scope_client(
    branch, phone='13800009999', include_view=True, include_suppliers=True,
    include_manage=True,
):
    user = User.objects.create_user(
        phone=phone, name='范围内对账员', password='test123456',
        role='manager', status='active', branch=branch,
    )
    ManagementScope.objects.create(user=user, branch=branch)
    if include_view:
        OperationGrant.objects.create(user=user, code='view_reconciliation')
    if include_suppliers:
        OperationGrant.objects.create(user=user, code='view_suppliers')
    if include_manage:
        OperationGrant.objects.create(user=user, code='manage_reconciliation')
    return user, _client_for(user)


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
        ['PO-1', 'sn-1', branch.name, '2026-09-01', '2026-09-01', '100.00'],
        ['PO-1', ' SN-1 ', branch.name, '2026-09-01', '2026-09-02', '100.00'],
    ]
    with pytest.raises(ValidationError) as exc:
        parse_workbook(_upload(rows), date(2026, 9, 1))
    assert str(exc.value.detail['errors'][0]['row']) == '3'
    assert '首次出现在第 2 行' in exc.value.detail['errors'][0]['message']


def test_import_rejects_entire_workbook_on_unknown_branch(branch):
    rows = [
        ['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-01', '100.00'],
        ['PO-2', 'SN-2', '不存在的分公司', '2026-09-01', '2026-09-01', '100.00'],
    ]
    with pytest.raises(ValidationError) as exc:
        parse_workbook(_upload(rows), date(2026, 9, 1))
    assert str(exc.value.detail['errors'][0]['row']) == '3'
    assert exc.value.detail['errors'][0]['value'] == '不存在的分公司'


@pytest.mark.django_db
@pytest.mark.parametrize('headers', [
    ['订单号', '序列号', '分公司', '起租日期', '记账日期', '记账天数', '月租金', '本月金额'],
    ['订单号', '序列号', '分公司', '记账日期', '起租日期', '月租金'],
    ['订单号', '序列号', '分公司', '起租日期', '记账日期', '月租金', '额外列'],
])
def test_import_requires_exact_six_column_header(headers):
    with pytest.raises(ValidationError) as exc:
        parse_workbook(_upload([['PO-1', 'SN-1', '分公司甲', '2026-09-01', '2026-09-01', '10.00']], headers=headers), date(2026, 9, 1))
    assert exc.value.detail['expectedHeaders'] == ['订单号', '序列号', '分公司', '起租日期', '记账日期', '月租金']
    assert exc.value.detail['actualHeaders'] == headers


@pytest.mark.django_db
def test_import_rejects_invalid_required_date_and_monthly_rent(branch):
    with pytest.raises(ValidationError) as exc:
        parse_workbook(_upload([
            ['PO-1', 'SN-1', branch.name, '2026/09/01', '2026-09-01', '10.00'],
            ['PO-2', 'SN-2', branch.name, '2026-09-01', '2026-09-01', '-1.00'],
        ]), date(2026, 9, 1))
    assert {(str(row['row']), str(row['field'])) for row in exc.value.detail['errors']} == {
        ('2', '起租日期'), ('3', '月租金'),
    }


@pytest.mark.django_db
def test_preview_returns_calculated_summary_without_upload_value_warnings_or_writes(branch):
    supplier = Supplier.objects.create(name='预览租赁商')
    result = preview_reconciliation_order(
        supplier.pk, '2026-09', _upload([
            ['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-20', '31.00'],
            ['PO-2', 'SN-2', branch.name, '2026-09-01', '2026-09-01', '20.00'],
        ]),
    )
    assert result['branch_count'] == 1
    assert result['order_count'] == 2
    assert result['row_count'] == 2
    assert result['total_amount'] == '31.37'
    assert result['calculation_warnings'] == []
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
                ['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-01', '10.00'],
                ['PO-2', 'SN-2', '不存在的分公司', '2026-09-01', '2026-09-01', '10.00'],
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
        'file': _upload([['PO-1', 'SN-1', branch.name, '2026-09-01', '2026-09-01', '10.00']], 'order.csv'),
    }
    assert manager_client.post('/api/reconciliation/tasks/preview', form, format='multipart').status_code == 403
    response = authenticated_client.post('/api/reconciliation/tasks/preview', form, format='multipart')
    assert response.status_code == 400
    assert 'xlsx' in response.data['detail']


@pytest.mark.django_db
@pytest.mark.parametrize('endpoint', ['preview', 'import'])
@pytest.mark.parametrize(('include_view', 'include_manage', 'include_suppliers', 'expected_status'), [
    (True, True, True, 200),
    (False, True, True, 403),
    (True, True, False, 403),
    (True, False, True, 403),
])
def test_reconciliation_preview_and_import_require_manage_and_supplier_view(
    branch, tmp_path, endpoint, include_view, include_manage, include_suppliers,
    expected_status,
):
    _user, client = _reconciliation_scope_client(
        branch, include_view=include_view, include_suppliers=include_suppliers,
        include_manage=include_manage,
    )
    supplier = Supplier.objects.create(name='预览导入双权限供应商')
    form = {
        'supplier': str(supplier.pk), 'period': '2026-09',
        'file': _upload([[
            'PO-PERMISSION', 'PERMISSION-SN', branch.name,
            '2026-09-01', '2026-09-01', '10.00',
        ]]),
    }

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            f'/api/reconciliation/tasks/{endpoint}', form, format='multipart',
        )

    assert response.status_code == expected_status, response.data


@pytest.mark.django_db
def test_upload_replacement_is_atomic_and_archived_task_cannot_be_overwritten(branch, admin_user, tmp_path):
    supplier = Supplier.objects.create(name='测试租赁商')
    item = Category.objects.create(
        asset_category='固定资产', item_category='电脑', asset_name='测试电脑',
        asset_code='A-a00008', unit='台', management_type='instance',
    )
    FixedAsset.objects.create(
        item=item, 内部编号='A-a00008-CS001-1', 序列号='SN-1', 当前状态='在用', branch=branch, 供应商=supplier.name,
    )
    rows = [['PO-1', 'sn-1', branch.name, '2026-09-01', '2026-09-01', '100.00']]
    with override_settings(MEDIA_ROOT=tmp_path):
        task, version = import_reconciliation_order(supplier.pk, '2026-09', _upload(rows), admin_user)
        assert version.version_number == 1
        assert version.comparisons.get().result_type == ReconciliationComparison.RESULT_MATCHED

        bad_rows = [['PO-2', '', branch.name, '2026-09-01', '2026-09-01', '200.00']]
        with pytest.raises(ValidationError):
            import_reconciliation_order(supplier.pk, '2026-09', _upload(bad_rows), admin_user)
        task.refresh_from_db()
        assert task.current_version_id == version.pk
        assert ReconciliationUploadVersion.objects.filter(task=task).count() == 1

        replacement, version2 = import_reconciliation_order(supplier.pk, '2026-09', _upload([
            ['PO-2', 'SN-1', branch.name, '2026-09-01', '2026-09-16', '100.00'],
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
            当前状态='在用', branch=instance_branch, 供应商=supplier.name,
        )
    FixedAsset.objects.create(
        item=item, 内部编号='A-a00001-CS001-3', 序列号='',
        当前状态='在库', branch=branch, 供应商=supplier.name,
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        _, version = import_reconciliation_order(supplier.pk, '2026-09', _upload([
            ['PO-1', 'OTHER', branch.name, '2026-09-01', '2026-09-01', '10.00'],
        ]), admin_user)
    assert version.comparisons.filter(result_type=ReconciliationComparison.RESULT_SYSTEM_DUPLICATE).count() == 2
    missing_serial = version.comparisons.get(
        result_type=ReconciliationComparison.RESULT_SYSTEM_MISSING_SERIAL,
    )
    assert missing_serial.system_serial_original == ''


@pytest.mark.django_db
def test_supplier_scope_isolates_foreign_serial_and_inherits_supplier_provenance(
    branch, second_branch, admin_user, tmp_path,
):
    supplier_a = Supplier.objects.create(name='供应商范围甲')
    supplier_b = Supplier.objects.create(name='供应商范围乙')
    assert not Supplier.objects.filter(name='未登记供应商').exists()
    item = Category.objects.create(
        asset_category='固定资产', item_category='电脑', asset_name='范围测试电脑',
        asset_code='A-a00008', unit='台', management_type='instance',
    )

    head_a = Transfer.objects.create(调拨日期=date(2026, 9, 1), 供应商=supplier_a.name)
    head_b = Transfer.objects.create(调拨日期=date(2026, 9, 2), 供应商=supplier_b.name)
    line_a = TransferLine.objects.create(transfer=head_a, item=item, 行号=1, 数量=1, 供应商=supplier_a.name)
    line_b = TransferLine.objects.create(transfer=head_b, item=item, 行号=1, 数量=1, 供应商=supplier_b.name)
    line_blank_a = TransferLine.objects.create(transfer=head_a, item=item, 行号=2, 数量=1, 供应商='')

    def asset(internal_code, serial, *, asset_supplier='', birth_line=None, asset_branch=branch):
        return FixedAsset.objects.create(
            item=item, 内部编号=internal_code, 序列号=serial,
            当前状态=FixedAsset.STATUS_IN_USE, branch=asset_branch,
            供应商=asset_supplier, birth_line=birth_line,
        )

    # Instance supplier wins over a conflicting birth-line supplier.
    asset('SCOPE-DIRECT', 'DIRECT', asset_supplier=supplier_a.name, birth_line=line_b)
    # A blank instance supplier falls back to the birth-line supplier.
    asset('SCOPE-LINE', 'LINE', birth_line=line_a)
    # A blank line supplier falls back to the birth document supplier.
    asset('SCOPE-HEAD', 'HEAD', birth_line=line_blank_a)
    # Same serial in another supplier must be excluded from this task's scope.
    asset('SCOPE-A-SAME', 'SAME', asset_supplier=supplier_a.name)
    asset('SCOPE-B-SAME', 'SAME', asset_supplier=supplier_b.name, asset_branch=second_branch)
    # Unknown provenance is diagnosed and does not become a system-only row.
    asset('SCOPE-UNKNOWN', 'UNKNOWN')
    asset('SCOPE-INVALID-SUPPLIER', 'INVALID', asset_supplier='未登记供应商')
    before_assets = list(FixedAsset.objects.order_by('内部编号').values_list(
        '内部编号', '序列号', '供应商', '当前状态', 'branch_id', 'birth_line_id',
    ))

    rows = [
        ['PO-DIRECT', 'direct', branch.name, '2026-09-01', '2026-09-01', '10.00'],
        ['PO-LINE', ' line ', branch.name, '2026-09-01', '2026-09-01', '10.00'],
        ['PO-HEAD', 'head', branch.name, '2026-09-01', '2026-09-01', '10.00'],
        ['PO-SAME', 'same', branch.name, '2026-09-01', '2026-09-01', '10.00'],
        ['PO-UNKNOWN', 'unknown', branch.name, '2026-09-01', '2026-09-01', '10.00'],
        ['PO-INVALID', 'invalid', branch.name, '2026-09-01', '2026-09-01', '10.00'],
    ]
    with override_settings(MEDIA_ROOT=tmp_path):
        _, version = import_reconciliation_order(supplier_a.pk, '2026-09', _upload(rows), admin_user)

    by_serial = {}
    for comparison in version.comparisons.select_related('order_row'):
        key = comparison.order_row.serial_normalized if comparison.order_row else comparison.system_serial_original
        by_serial.setdefault(key, []).append(comparison)

    for serial in ('DIRECT', 'LINE', 'HEAD', 'SAME'):
        assert [row.result_type for row in by_serial[serial]] == [ReconciliationComparison.RESULT_MATCHED]
    assert [row.result_type for row in by_serial['UNKNOWN']] == [ReconciliationComparison.RESULT_ORDER_ONLY]
    assert [row.result_type for row in by_serial['INVALID']] == [ReconciliationComparison.RESULT_ORDER_ONLY]
    assert not version.comparisons.filter(
        system_serial_original='SAME',
        result_type__in=[
            ReconciliationComparison.RESULT_SYSTEM_ONLY,
            ReconciliationComparison.RESULT_SYSTEM_DUPLICATE,
        ],
    ).exists()

    diagnostics = version.summary['scope_diagnostics']
    assert diagnostics['excluded_count'] >= 2
    assert diagnostics['foreign_supplier_serials'] == ['SAME']
    assert diagnostics['unknown_supplier_serials'] == ['INVALID', 'UNKNOWN']
    assert diagnostics['unknown_supplier_count'] >= 2
    assert list(FixedAsset.objects.order_by('内部编号').values_list(
        '内部编号', '序列号', '供应商', '当前状态', 'branch_id', 'birth_line_id',
    )) == before_assets


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
                    'PO-API', 'API-SN', branch.name, '2026-09-01', '2026-09-20', '31.00',
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
def test_task_list_api_filters_and_paginates(authenticated_client, admin_user):
    supplier = Supplier.objects.create(name='分页供应商')
    for month in ('2026-07-01', '2026-08-01', '2026-09-01'):
        ReconciliationTask.objects.create(
            supplier=supplier, period=month, created_by=admin_user,
        )

    started = perf_counter()
    response = authenticated_client.get(
        '/api/reconciliation/tasks?supplier={}&period=2026-08&page=1&pageSize=1'.format(supplier.pk),
    )
    elapsed_ms = (perf_counter() - started) * 1000

    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['page'] == 1
    assert response.data['page_size'] == 1
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['period'] == '2026-08'
    assert elapsed_ms < 5000


@pytest.mark.django_db
def test_task_detail_api_filters_and_paginates_comparisons(authenticated_client, admin_user, branch, second_branch):
    supplier = Supplier.objects.create(name='明细分页供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/test.xlsx',
        uploaded_by=admin_user, row_count=0,
        summary={
            'row_count': 0, 'counts': {'matched': 1, 'system_only': 2},
            'pending_count': 2, 'total_amount': '0.00', 'branch_totals': [],
            'comparison_count': 3, 'scope_diagnostics': {},
        },
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    for serial, result, instance_branch in [
        ('PAGE-A', ReconciliationComparison.RESULT_SYSTEM_ONLY, branch),
        ('PAGE-B', ReconciliationComparison.RESULT_SYSTEM_ONLY, second_branch),
        ('PAGE-C', ReconciliationComparison.RESULT_MATCHED, branch),
    ]:
        ReconciliationComparison.objects.create(
            version=version, result_type=result,
            system_serial_original=serial, system_branch_id=instance_branch.pk,
            system_branch_name=instance_branch.name,
        )

    started = perf_counter()
    response = authenticated_client.get(
        f'/api/reconciliation/tasks/{task.pk}?result=system_only&branch={branch.pk}&serial=PAGE-A&page=1&pageSize=1',
    )
    elapsed_ms = (perf_counter() - started) * 1000

    assert response.status_code == 200
    assert response.data['comparison_total'] == 1
    assert response.data['comparison_page'] == 1
    assert response.data['comparison_page_size'] == 1
    assert len(response.data['comparisons']) == 1
    assert response.data['comparisons'][0]['serial'] == 'PAGE-A'
    assert elapsed_ms < 5000
    assert {row['value'] for row in response.data['branch_options']} == {
        str(branch.pk), str(second_branch.pk),
    }
    assert len(response.data['versions']) == 1
    assert response.data['versions'][0]['version_number'] == 1


@pytest.mark.django_db
def test_reconciliation_reads_and_export_are_limited_to_account_branch_scope(
    admin_user, branch, second_branch,
):
    _scope_user, client = _reconciliation_scope_client(branch, include_suppliers=True)
    supplier = Supplier.objects.create(name='范围过滤供应商')
    unrelated_supplier = Supplier.objects.create(name='无可见任务的供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/scoped.xlsx',
        uploaded_by=admin_user, row_count=3,
        summary={
            'row_count': 3, 'counts': {'order_only': 2, 'system_only': 1},
            'pending_count': 3, 'total_amount': '999.00',
            'branch_totals': [{'branch_id': str(second_branch.pk), 'branch_name': second_branch.name}],
            'comparison_count': 3, 'scope_diagnostics': {'unknown_supplier_serials': ['SECRET-SN']},
        },
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    visible_order = ReconciliationOrderRow.objects.create(
        version=version, row_number=2, order_number='PO-VISIBLE',
        serial_original='VISIBLE-SN', serial_normalized='VISIBLE-SN',
        supplier_branch_text=branch.name, branch=branch,
        lease_start_date=date(2026, 9, 1), accounting_date=date(2026, 9, 1),
        billing_days=30, monthly_rent=Decimal('10.00'), month_amount=Decimal('10.00'),
    )
    mixed_order = ReconciliationOrderRow.objects.create(
        version=version, row_number=3, order_number='PO-MIXED',
        serial_original='MIXED-ORDER-SN', serial_normalized='MIXED-ORDER-SN',
        supplier_branch_text=branch.name, branch=branch,
        lease_start_date=date(2026, 9, 1), accounting_date=date(2026, 9, 1),
        billing_days=30, monthly_rent=Decimal('20.00'), month_amount=Decimal('20.00'),
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
        order_row=visible_order,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        system_serial_original='FOREIGN-SN', system_branch_id=second_branch.pk,
        system_branch_name=second_branch.name,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_BRANCH_MISMATCH,
        order_row=mixed_order, system_serial_original='MIXED-SYSTEM-SN',
        system_branch_id=second_branch.pk, system_branch_name=second_branch.name,
    )

    listing = client.get('/api/reconciliation/tasks')
    assert listing.status_code == 200
    assert listing.data['count'] == 1
    supplier_rows = {row['id']: row['name'] for row in listing.data['suppliers']}
    assert supplier_rows == {
        str(supplier.pk): supplier.name,
        str(unrelated_supplier.pk): unrelated_supplier.name,
    }
    summary = listing.data['results'][0]
    assert summary['row_count'] == 1
    assert summary['comparison_count'] == 1
    assert summary['counts'] == {'order_only': 1}
    assert summary['total_amount'] == '10.00'
    assert summary['branch_totals'][0]['branch_id'] == str(branch.pk)
    assert summary['scope_diagnostics'] == {}

    detail = client.get(f'/api/reconciliation/tasks/{task.pk}')
    assert detail.status_code == 200
    assert detail.data['comparison_total'] == 1
    assert [row['serial'] for row in detail.data['comparisons']] == ['VISIBLE-SN']
    assert detail.data['branch_options'] == [{'value': str(branch.pk), 'label': branch.name}]
    assert detail.data['versions'][0]['row_count'] == 1

    exported = client.get(f'/api/reconciliation/export?task={task.pk}')
    assert exported.status_code == 200
    from openpyxl import load_workbook
    sheet = load_workbook(BytesIO(exported.content), read_only=True).active
    exported_text = '\n'.join(str(value) for row in sheet.iter_rows(values_only=True) for value in row)
    assert 'VISIBLE-SN' in exported_text
    assert 'FOREIGN-SN' not in exported_text
    assert 'MIXED-SYSTEM-SN' not in exported_text


@pytest.mark.django_db
def test_reconciliation_manage_requires_view_for_all_reads_and_writes(
    admin_user, branch, second_branch, tmp_path,
):
    _scope_user, client = _reconciliation_scope_client(
        branch, phone='13800009998', include_view=False, include_suppliers=True,
    )
    supplier = Supplier.objects.create(name='维护权限范围测试供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 10, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/manage-only.xlsx',
        uploaded_by=admin_user, row_count=3,
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    visible_order = ReconciliationOrderRow.objects.create(
        version=version, row_number=2, order_number='PO-MANAGE-VISIBLE',
        serial_original='MANAGE-VISIBLE-SN', serial_normalized='MANAGE-VISIBLE-SN',
        supplier_branch_text=branch.name, branch=branch,
        lease_start_date=date(2026, 10, 1), accounting_date=date(2026, 10, 1),
        billing_days=31, monthly_rent=Decimal('10.00'), month_amount=Decimal('10.00'),
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY,
        order_row=visible_order,
    )
    visible_issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='manage-only-visible-issue',
        issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        serial_normalized='MANAGE-ISSUE-SN', first_period=task.period, last_period=task.period,
    )
    foreign_issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='manage-only-foreign-issue',
        issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        serial_normalized='MANAGE-FOREIGN-ISSUE-SN', first_period=task.period, last_period=task.period,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        issue=visible_issue, system_serial_original='MANAGE-ISSUE-SN',
        system_branch_id=branch.pk, system_branch_name=branch.name,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        issue=foreign_issue, system_serial_original='MANAGE-FOREIGN-ISSUE-SN',
        system_branch_id=second_branch.pk, system_branch_name=second_branch.name,
    )

    initial_version_count = ReconciliationUploadVersion.objects.count()
    upload_rows = [[
        'PO-MANAGE-ONLY', 'MANAGE-ONLY-SN', branch.name,
        '2026-11-01', '2026-11-01', '10.00',
    ]]
    import_data = {
        'supplier': str(supplier.pk), 'period': '2026-11',
        'file': _upload(upload_rows),
    }
    replace_data = {
        'supplier': str(supplier.pk), 'period': '2026-10',
        'file': _upload(upload_rows),
    }

    assert client.get('/api/reconciliation/tasks').status_code == 403
    assert client.get(f'/api/reconciliation/tasks/{task.pk}').status_code == 403
    assert client.post(f'/api/reconciliation/tasks/{task.pk}/archive').status_code == 403
    assert client.get(f'/api/reconciliation/export?task={task.pk}').status_code == 403

    with override_settings(MEDIA_ROOT=tmp_path):
        assert client.post(
            '/api/reconciliation/tasks/preview', import_data, format='multipart',
        ).status_code == 403
        assert client.post(
            '/api/reconciliation/tasks/import', import_data, format='multipart',
        ).status_code == 403
        assert client.post(
            '/api/reconciliation/tasks/import', replace_data, format='multipart',
        ).status_code == 403

    task.refresh_from_db()
    assert task.status == ReconciliationTask.STATUS_DRAFT
    assert ReconciliationUploadVersion.objects.count() == initial_version_count
    assert not ReconciliationTask.objects.filter(
        supplier=supplier, period=date(2026, 11, 1),
    ).exists()


@pytest.mark.django_db
def test_reconciliation_reads_and_writes_require_supplier_view(
    admin_user, branch,
):
    _user, client = _reconciliation_scope_client(
        branch, phone='13800009997', include_view=True, include_suppliers=False,
        include_manage=True,
    )
    supplier = Supplier.objects.create(name='供应商前置校验')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 10, 1), created_by=admin_user,
    )
    issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='supplier-prerequisite-issue',
        issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        serial_normalized='SUPPLIER-PREREQUISITE',
        first_period=task.period, last_period=task.period,
    )

    assert client.get('/api/reconciliation/tasks').status_code == 403
    assert client.get(f'/api/reconciliation/tasks/{task.pk}').status_code == 403
    assert client.post(f'/api/reconciliation/tasks/{task.pk}/archive').status_code == 403
    assert client.get(f'/api/reconciliation/export?task={task.pk}').status_code == 403


@pytest.mark.django_db
def test_reconciliation_scope_blocks_cross_branch_issue_updates_and_task_archives(
    admin_user, branch, second_branch,
):
    _scope_user, client = _reconciliation_scope_client(branch)
    supplier = Supplier.objects.create(name='范围写入供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/mixed-scope.xlsx',
        uploaded_by=admin_user,
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    shared_issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='shared-branch-issue',
        issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        serial_normalized='SHARED-SN', first_period=task.period, last_period=task.period,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        issue=shared_issue, system_serial_original='SHARED-SN',
        system_branch_id=branch.pk, system_branch_name=branch.name,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        issue=shared_issue, system_serial_original='SHARED-SN',
        system_branch_id=second_branch.pk, system_branch_name=second_branch.name,
    )

    assert client.post(f'/api/reconciliation/tasks/{task.pk}/archive').status_code == 404
    task.refresh_from_db()
    assert task.status == ReconciliationTask.STATUS_DRAFT

    scoped_supplier = Supplier.objects.create(name='本分公司范围供应商')
    scoped_task = ReconciliationTask.objects.create(
        supplier=scoped_supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    scoped_version = ReconciliationUploadVersion.objects.create(
        task=scoped_task, version_number=1, file='reconciliation/in-scope.xlsx',
        uploaded_by=admin_user,
    )
    scoped_task.current_version = scoped_version
    scoped_task.save(update_fields=['current_version'])
    scoped_issue = ReconciliationIssue.objects.create(
        supplier=scoped_supplier, issue_key='in-scope-issue',
        issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        serial_normalized='IN-SCOPE-SN', first_period=scoped_task.period, last_period=scoped_task.period,
    )
    ReconciliationComparison.objects.create(
        version=scoped_version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        issue=scoped_issue, system_serial_original='IN-SCOPE-SN',
        system_branch_id=branch.pk, system_branch_name=branch.name,
    )



@pytest.mark.django_db
def test_reconciliation_import_checks_workbook_and_existing_task_scope(
    admin_user, branch, second_branch, tmp_path,
):
    _scope_user, client = _reconciliation_scope_client(branch)
    supplier = Supplier.objects.create(name='范围导入供应商')
    foreign_rows = [[
        'PO-FOREIGN', 'FOREIGN-IMPORT-SN', second_branch.name,
        '2026-09-01', '2026-09-01', '10.00',
    ]]

    preview = client.post(
        '/api/reconciliation/tasks/preview',
        {'supplier': str(supplier.pk), 'period': '2026-09', 'file': _upload(foreign_rows)},
        format='multipart',
    )
    imported = client.post(
        '/api/reconciliation/tasks/import',
        {'supplier': str(supplier.pk), 'period': '2026-09', 'file': _upload(foreign_rows)},
        format='multipart',
    )
    assert preview.status_code == 400
    assert imported.status_code == 400
    assert not ReconciliationTask.objects.filter(supplier=supplier).exists()

    existing = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=existing, version_number=1, file='reconciliation/old-mixed.xlsx',
        uploaded_by=admin_user,
    )
    existing.current_version = version
    existing.save(update_fields=['current_version'])
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        system_branch_id=branch.pk, system_branch_name=branch.name,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        system_branch_id=second_branch.pk, system_branch_name=second_branch.name,
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        replace = client.post(
            '/api/reconciliation/tasks/import',
            {
                'supplier': str(supplier.pk), 'period': '2026-09',
                'file': _upload([[
                    'PO-IN-SCOPE', 'IN-SCOPE-SN', branch.name,
                    '2026-09-01', '2026-09-01', '10.00',
                ]]),
            },
            format='multipart',
        )
    assert replace.status_code == 400
    existing.refresh_from_db()
    assert existing.current_version_id == version.pk

    with override_settings(MEDIA_ROOT=tmp_path):
        allowed = client.post(
            '/api/reconciliation/tasks/import',
            {
                'supplier': str(supplier.pk), 'period': '2026-10',
                'file': _upload([[
                    'PO-IN-SCOPE', 'IN-SCOPE-SN', branch.name,
                    '2026-10-01', '2026-10-01', '10.00',
                ]]),
            },
            format='multipart',
        )
    assert allowed.status_code == 200, allowed.data


@pytest.mark.django_db
def test_task_detail_query_count_stays_bounded_as_comparisons_grow(
    authenticated_client, admin_user, record_property,
):
    supplier = Supplier.objects.create(name='查询规模供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/query-scale.xlsx',
        uploaded_by=admin_user, row_count=0,
        summary={
            'row_count': 0, 'counts': {'matched': 0}, 'pending_count': 0,
            'total_amount': '0.00', 'branch_totals': [],
            'comparison_count': 0, 'scope_diagnostics': {},
        },
    )
    task.current_version = version
    task.save(update_fields=['current_version'])

    def add_comparisons(count):
        ReconciliationComparison.objects.bulk_create([
            ReconciliationComparison(
                version=version, result_type=ReconciliationComparison.RESULT_MATCHED,
                system_serial_original=f'SCALE-{index}',
            )
            for index in range(count)
        ], batch_size=500)

    add_comparisons(10)
    started = perf_counter()
    with CaptureQueriesContext(connection) as small_queries:
        small_response = authenticated_client.get(
            f'/api/reconciliation/tasks/{task.pk}?result=all&page=1&pageSize=10',
        )
    small_elapsed_ms = (perf_counter() - started) * 1000
    add_comparisons(990)
    started = perf_counter()
    with CaptureQueriesContext(connection) as large_queries:
        large_response = authenticated_client.get(
            f'/api/reconciliation/tasks/{task.pk}?result=all&page=1&pageSize=10',
        )
    large_elapsed_ms = (perf_counter() - started) * 1000

    assert small_response.status_code == large_response.status_code == 200
    assert small_response.data['comparison_total'] == 10
    assert large_response.data['comparison_total'] == 1000
    assert len(small_response.data['comparisons']) == len(large_response.data['comparisons']) == 10
    assert len(large_queries) <= len(small_queries) + 1
    record_property('detail_10_rows_ms', round(small_elapsed_ms, 2))
    record_property('detail_1000_rows_ms', round(large_elapsed_ms, 2))
    assert large_elapsed_ms < 5000


@pytest.mark.django_db
def test_task_list_query_count_stays_bounded_as_history_grows(
    authenticated_client, admin_user, record_property,
):
    supplier = Supplier.objects.create(name='列表查询规模供应商')

    def add_tasks(start_month, count):
        for offset in range(count):
            month_index = start_month + offset
            year = 2020 + (month_index - 1) // 12
            month = (month_index - 1) % 12 + 1
            task = ReconciliationTask.objects.create(
                supplier=supplier, period=date(year, month, 1), created_by=admin_user,
            )
            version = ReconciliationUploadVersion.objects.create(
                task=task, version_number=1,
                file=f'reconciliation/list-{month_index}.xlsx',
                uploaded_by=admin_user, row_count=0,
                summary={
                    'row_count': 0, 'counts': {}, 'pending_count': 0,
                    'total_amount': '0.00', 'branch_totals': [],
                    'comparison_count': 0, 'scope_diagnostics': {},
                },
            )
            task.current_version = version
            task.save(update_fields=['current_version'])

    add_tasks(1, 5)
    started = perf_counter()
    with CaptureQueriesContext(connection) as small_queries:
        small_response = authenticated_client.get('/api/reconciliation/tasks?pageSize=5')
    small_elapsed_ms = (perf_counter() - started) * 1000
    add_tasks(6, 45)
    started = perf_counter()
    with CaptureQueriesContext(connection) as large_queries:
        large_response = authenticated_client.get('/api/reconciliation/tasks?pageSize=5')
    large_elapsed_ms = (perf_counter() - started) * 1000

    assert small_response.status_code == large_response.status_code == 200
    assert small_response.data['count'] == 5
    assert large_response.data['count'] == 50
    assert len(small_response.data['results']) == len(large_response.data['results']) == 5
    assert len(large_queries) <= len(small_queries) + 1
    record_property('list_5_tasks_ms', round(small_elapsed_ms, 2))
    record_property('list_50_tasks_ms', round(large_elapsed_ms, 2))
    assert large_elapsed_ms < 5000


@pytest.mark.django_db
def test_import_issue_queries_are_batched_as_order_differences_grow(
    branch, admin_user, tmp_path, record_property,
):
    def import_with_order_rows(count, supplier_name, month):
        supplier = Supplier.objects.create(name=supplier_name)
        rows = [
            [f'PO-{index}', f'BATCH-{month}-{index}', branch.name, '2026-09-01', '2026-09-01', '10.00']
            for index in range(count)
        ]
        started = perf_counter()
        with override_settings(MEDIA_ROOT=tmp_path), CaptureQueriesContext(connection) as queries:
            _task, version = import_reconciliation_order(
                supplier.pk, month, _upload(rows), admin_user,
            )
        elapsed_ms = (perf_counter() - started) * 1000
        assert version.comparisons.count() == count
        return len(queries), elapsed_ms

    small_count, small_elapsed_ms = import_with_order_rows(10, '批量差异供应商甲', '2026-09')
    large_count, large_elapsed_ms = import_with_order_rows(50, '批量差异供应商乙', '2026-10')

    assert large_count <= small_count + 3
    record_property('import_10_rows_ms', round(small_elapsed_ms, 2))
    record_property('import_50_rows_ms', round(large_elapsed_ms, 2))
    assert large_elapsed_ms < 5000


@pytest.mark.django_db
def test_archive_gate_blocks_any_non_matched_comparison(authenticated_client, admin_user, branch):
    supplier = Supplier.objects.create(name='归档门禁供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/gate.xlsx',
        uploaded_by=admin_user,
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='gate-issue',
        issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        serial_normalized='GATE-SN', first_period=task.period, last_period=task.period,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        issue=issue, system_serial_original='GATE-SN',
        system_branch_id=branch.pk, system_branch_name=branch.name,
    )
    resp = authenticated_client.post(f'/api/reconciliation/tasks/{task.pk}/archive')
    assert resp.status_code == 400
    assert '1 条差异' in resp.data['detail']


@pytest.mark.django_db
def test_pending_count_equals_diff_count_without_conclusion_filter(authenticated_client, admin_user):
    """pending_count counts ALL non-matched diffs (no conclusion/status filter)."""
    supplier = Supplier.objects.create(name='待处理无结论供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/pending-raw.xlsx',
        uploaded_by=admin_user, row_count=0, summary={},
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='raw-pending-issue',
        issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
        serial_normalized='RAW-SN', first_period=task.period, last_period=task.period,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY, issue=issue,
    )
    response = authenticated_client.get('/api/reconciliation/tasks')
    assert response.status_code == 200
    assert response.data['results'][0]['pending_count'] == 1
