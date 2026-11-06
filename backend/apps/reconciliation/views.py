import calendar
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.decorators import audit_log
from apps.audit.utils import create_audit_log
from apps.reconciliation.models import (
    ReconciliationComparison,
    ReconciliationIssue,
    ReconciliationIssueHistory,
    ReconciliationTask,
)
from apps.reconciliation.services import (
    build_branch_summary,
    build_payment_summary,
    _comparison_queryset_for_scope,
    import_reconciliation_order,
    preview_reconciliation_order,
    rematch_task,
    task_summary,
    update_issue,
)
from apps.suppliers.models import Supplier
from apps.permissions.permissions import OperationPermission
from apps.permissions.scope import resolve_user_scope


class ReconciliationPermissionView(APIView):
    permission_classes = [IsAuthenticated, OperationPermission]

    def get_required_operations_any(self, request):
        # Maintainers need read access to the scoped work queue they maintain.
        # Export overrides this so data extraction still requires view access.
        if request.method == 'GET':
            return ('view_reconciliation', 'manage_reconciliation')
        return None

    def get_required_operation(self, request):
        return 'view_reconciliation' if request.method == 'GET' else 'manage_reconciliation'


class ReconciliationImportPermissionView(ReconciliationPermissionView):
    def get_required_operations(self, request):
        return ('manage_reconciliation', 'view_suppliers')


def _task_queryset_for_scope(queryset, scope, require_all_comparisons=False):
    if scope.all:
        return queryset

    visible_comparisons = _comparison_queryset_for_scope(
        ReconciliationComparison.objects.all(), scope,
    )
    visible_for_task = visible_comparisons.filter(version_id=OuterRef('current_version_id'))
    queryset = queryset.annotate(_has_scoped_comparisons=Exists(visible_for_task)).filter(
        _has_scoped_comparisons=True,
    )
    if require_all_comparisons:
        all_for_task = ReconciliationComparison.objects.filter(version_id=OuterRef('current_version_id'))
        hidden_for_task = all_for_task.exclude(pk__in=visible_comparisons.values('pk'))
        queryset = queryset.annotate(_has_hidden_comparisons=Exists(hidden_for_task)).filter(
            _has_hidden_comparisons=False,
        )
    return queryset


def _issue_queryset_for_scope(queryset, scope):
    if scope.all:
        return queryset

    visible_comparisons = _comparison_queryset_for_scope(
        ReconciliationComparison.objects.filter(issue_id__isnull=False), scope,
    )
    visible_issue_ids = visible_comparisons.values('issue_id')
    hidden_issue_ids = ReconciliationComparison.objects.filter(
        issue_id__isnull=False,
    ).exclude(pk__in=visible_comparisons.values('pk')).values('issue_id')
    return queryset.filter(pk__in=visible_issue_ids).exclude(pk__in=hidden_issue_ids)


def _scoped_task_summary(task, scope):
    version = task.current_version
    if version is None:
        return {
            'row_count': 0, 'counts': {}, 'pending_count': 0,
            'total_amount': '0.00', 'branch_totals': [],
            'comparison_count': 0, 'scope_diagnostics': {},
        }

    comparisons = _comparison_queryset_for_scope(version.comparisons.all(), scope)
    counts = dict(
        comparisons.values('result_type').annotate(count=Count('pk'))
        .values_list('result_type', 'count')
    )
    visible_issue_ids = _issue_queryset_for_scope(
        ReconciliationIssue.objects.all(), scope,
    ).values('pk')
    pending_count = comparisons.exclude(
        result_type=ReconciliationComparison.RESULT_MATCHED,
    ).filter(
        issue_id__in=visible_issue_ids,
        issue__status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
        issue__conclusion_type='',
    ).count()
    order_rows = version.order_rows.filter(comparisons__in=comparisons).distinct()
    branch_totals = []
    for bucket in order_rows.values('branch_id', 'branch__name').annotate(
        row_count=Count('pk'), monthly_rent=Sum('monthly_rent'), month_amount=Sum('month_amount'),
    ):
        branch_totals.append({
            'branch_id': str(bucket['branch_id']), 'branch_name': bucket['branch__name'],
            'row_count': bucket['row_count'],
            'monthly_rent': str((bucket['monthly_rent'] or Decimal('0.00')).quantize(Decimal('0.01'))),
            'month_amount': str((bucket['month_amount'] or Decimal('0.00')).quantize(Decimal('0.01'))),
        })
    total = order_rows.aggregate(total=Sum('month_amount'))['total'] or Decimal('0.00')
    return {
        'row_count': order_rows.count(), 'counts': counts, 'pending_count': pending_count,
        'total_amount': str(total.quantize(Decimal('0.01'))), 'branch_totals': branch_totals,
        'comparison_count': sum(counts.values()), 'scope_diagnostics': {},
    }


def _task_payload(task, pending_count=None, scope=None):
    summary = (
        _scoped_task_summary(task, scope)
        if scope is not None and not scope.all
        else task_summary(task, pending_count=pending_count)
    )
    version = task.current_version
    return {
        'id': str(task.pk), 'supplier_id': str(task.supplier_id), 'supplier_name': task.supplier.name,
        'period': task.period.strftime('%Y-%m'), 'status': task.status,
        'created_at': task.created_at, 'updated_at': task.updated_at,
        'archived_at': task.archived_at, 'current_version': version.version_number if version else None,
        'uploaded_by': (
            version.uploaded_by.name if version.uploaded_by else version.uploaded_by_name
        ) if version else None,
        'uploaded_at': version.created_at if version else None,
        **summary,
    }


def _comparison_payload(comp, task_period=None, include_issue=True):
    order = comp.order_row
    issue = comp.issue if include_issue else None
    future_billing = False
    if order:
        period = task_period or order.version.task.period
        month_end_day = calendar.monthrange(period.year, period.month)[1]
        month_end = period.replace(day=month_end_day)
        future_billing = order.accounting_date > month_end
    return {
        'id': str(comp.pk), 'result_type': comp.result_type,
        'serial': order.serial_original if order else comp.system_serial_original,
        'normalized_serial': order.serial_normalized if order else issue.serial_normalized if issue else '',
        'order_number': order.order_number if order else '',
        'supplier_branch': order.supplier_branch_text if order else '',
        'supplier_branch_id': str(order.branch_id) if order else None,
        'system_branch': comp.system_branch_name,
        'system_branch_id': str(comp.system_branch_id) if comp.system_branch_id else None,
        'internal_code': comp.internal_code,
        'system_status': comp.system_status,
        'item_code': comp.item_code,
        'item_name': comp.item_name,
        'lease_start_date': order.lease_start_date.isoformat() if order else None,
        'accounting_date': order.accounting_date.isoformat() if order else None,
        'billing_days': order.billing_days if order else None,
        'monthly_rent': str(order.monthly_rent) if order else None,
        'month_amount': str(order.month_amount) if order else None,
        'uploaded_billing_days': order.uploaded_billing_days if order else None,
        'uploaded_month_amount': str(order.uploaded_month_amount) if order and order.uploaded_month_amount is not None else None,
        'billing_status': 'not_started' if future_billing else 'billable' if order else None,
        'issue': {
            'id': str(issue.pk), 'status': issue.status, 'conclusion': issue.conclusion,
            'conclusion_type': issue.conclusion_type,
            'note': issue.note, 'first_period': issue.first_period.strftime('%Y-%m'),
            'last_period': issue.last_period.strftime('%Y-%m'),
            'handled_by': issue.handled_by.name if issue.handled_by else issue.handled_by_name or None,
            'handled_at': issue.handled_at,
        } if issue else None,
    }


class ReconciliationTaskListView(ReconciliationPermissionView):
    def get(self, request):
        scope = resolve_user_scope(request.user)
        visible_tasks = _task_queryset_for_scope(
            ReconciliationTask.objects.select_related('supplier', 'current_version__uploaded_by').all(),
            scope,
        )
        tasks = visible_tasks
        supplier = request.query_params.get('supplier')
        period = request.query_params.get('period')
        if supplier:
            tasks = tasks.filter(supplier_id=supplier)
        if period:
            try:
                tasks = tasks.filter(period=date.fromisoformat(f'{period}-01'))
            except ValueError:
                return Response({'detail': '月份格式必须为 YYYY-MM'}, status=400)
        try:
            page_number = max(int(request.query_params.get('page', 1) or 1), 1)
            page_size = min(max(int(request.query_params.get('pageSize', 20) or 20), 1), 100)
        except (TypeError, ValueError):
            return Response({'detail': '分页参数必须为正整数'}, status=400)
        periods = [period.strftime('%Y-%m') for period in visible_tasks.values_list(
            'period', flat=True,
        ).distinct().order_by('-period')]
        page = Paginator(tasks, page_size).get_page(page_number)
        page_tasks = list(page.object_list)
        version_ids = [task.current_version_id for task in page_tasks if task.current_version_id]
        if scope.all:
            pending_by_version = dict(
                ReconciliationComparison.objects.filter(version_id__in=version_ids)
                .exclude(result_type=ReconciliationComparison.RESULT_MATCHED)
                .filter(
                    issue__status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
                    issue__conclusion_type='',
                ).values('version_id').annotate(total=Count('id')).values_list('version_id', 'total')
            )
        else:
            pending_by_version = {}
        unresolved_groups = list(_issue_queryset_for_scope(ReconciliationIssue.objects.filter(
            status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
        ), scope).values(
            'supplier_id', 'supplier__name', 'first_period',
        ).annotate(issue_count=Count('pk', distinct=True)).order_by(
            'supplier__name', '-first_period',
        ))
        if request.user.can('view_suppliers'):
            supplier_options = Supplier.objects.order_by('name').values('id', 'name')
            suppliers = [{'id': str(row['id']), 'name': row['name']} for row in supplier_options]
        else:
            suppliers = []
        return Response({
            'suppliers': suppliers,
            'results': [
                _task_payload(
                    task, pending_by_version.get(task.current_version_id, 0), scope=scope,
                )
                for task in page_tasks
            ],
            'count': page.paginator.count,
            'page': page.number,
            'page_size': page_size,
            'periods': periods,
            'unresolved_summary': {
                'total_count': sum(group['issue_count'] for group in unresolved_groups),
                'groups': [{
                    'supplier_id': str(group['supplier_id']),
                    'supplier_name': group['supplier__name'],
                    'first_period': group['first_period'].strftime('%Y-%m'),
                    'count': group['issue_count'],
                } for group in unresolved_groups],
            },
        })


class ReconciliationTaskPreviewView(ReconciliationImportPermissionView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'detail': '请选择订单文件'}, status=400)
        if not upload.name.lower().endswith('.xlsx'):
            return Response({'detail': '目前仅支持 .xlsx 文件'}, status=400)
        return Response(preview_reconciliation_order(
            request.data.get('supplier'), request.data.get('period'), upload, user=request.user,
        ))


class ReconciliationTaskUploadView(ReconciliationImportPermissionView):
    parser_classes = [MultiPartParser]

    @audit_log(action='import', resource_type='ReconciliationTask', description_template='导入/替换月度租赁对账订单')
    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'detail': '请选择订单文件'}, status=400)
        if not upload.name.lower().endswith('.xlsx'):
            return Response({'detail': '目前仅支持 .xlsx 文件'}, status=400)
        task, _version = import_reconciliation_order(
            request.data.get('supplier'), request.data.get('period'), upload, request.user,
        )
        return Response(
            _task_payload(task, scope=resolve_user_scope(request.user)),
            status=status.HTTP_200_OK,
        )


class ReconciliationTaskDetailView(ReconciliationPermissionView):
    def get(self, request, pk):
        scope = resolve_user_scope(request.user)
        task = get_object_or_404(
            _task_queryset_for_scope(
                ReconciliationTask.objects.select_related('supplier', 'current_version__uploaded_by'),
                scope,
            ),
            pk=pk,
        )
        payload = _task_payload(task, scope=scope)
        if task.current_version:
            scoped_comps = _comparison_queryset_for_scope(task.current_version.comparisons.all(), scope)
            comps = scoped_comps.select_related(
                'order_row__branch', 'order_row__version__task', 'issue__handled_by',
            ).all()
            visible_issue_ids_for_scope = _issue_queryset_for_scope(
                ReconciliationIssue.objects.all(), scope,
            ).values('pk')
            result_filter = request.query_params.get('result')
            branch_filter = request.query_params.get('branch')
            serial_filter = (request.query_params.get('serial') or '').strip()
            if result_filter:
                if result_filter == 'pending':
                    comps = comps.exclude(result_type=ReconciliationComparison.RESULT_MATCHED).filter(
                        issue_id__in=visible_issue_ids_for_scope,
                        issue__status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
                        issue__conclusion_type='',
                    )
                elif result_filter == 'differences':
                    comps = comps.exclude(result_type=ReconciliationComparison.RESULT_MATCHED)
                elif result_filter != 'all':
                    comps = comps.filter(result_type=result_filter)
            if branch_filter:
                comps = comps.filter(
                    Q(order_row__branch_id=branch_filter) | Q(system_branch_id=branch_filter),
                )
            if serial_filter:
                comps = comps.filter(
                    Q(order_row__serial_normalized__icontains=serial_filter)
                    | Q(system_serial_original__icontains=serial_filter)
                )
            try:
                page_number = max(int(request.query_params.get('page', 1) or 1), 1)
                page_size = min(max(int(request.query_params.get('pageSize', 50) or 50), 1), 100)
            except (TypeError, ValueError):
                return Response({'detail': '分页参数必须为正整数'}, status=400)
            page = Paginator(comps, page_size).get_page(page_number)
            visible_issue_ids = set(_issue_queryset_for_scope(
                ReconciliationIssue.objects.filter(pk__in=scoped_comps.values('issue_id')),
                scope,
            ).values_list('pk', flat=True))
            payload['comparisons'] = [
                _comparison_payload(
                    comp, task.period,
                    include_issue=scope.all or comp.issue_id in visible_issue_ids,
                )
                for comp in page.object_list
            ]
            payload['comparison_total'] = page.paginator.count
            payload['comparison_page'] = page.number
            payload['comparison_page_size'] = page_size
            order_branches = scoped_comps.filter(
                order_row__branch_id__isnull=False,
            ).values_list('order_row__branch_id', 'order_row__branch__name').distinct()
            system_branches = scoped_comps.filter(
                system_branch_id__isnull=False,
            ).values_list('system_branch_id', 'system_branch_name').distinct()
            branch_options = {
                str(branch_id): name
                for branch_id, name in [*order_branches, *system_branches]
                if branch_id and name
            }
            payload['branch_options'] = [
                {'value': value, 'label': label}
                for value, label in sorted(branch_options.items(), key=lambda pair: pair[1])
            ]
            versions = []
            for version in task.versions.select_related('uploaded_by').all():
                version_comps = _comparison_queryset_for_scope(version.comparisons.all(), scope)
                if not scope.all and not version_comps.exists():
                    continue
                row_count = version.row_count if scope.all else version.order_rows.filter(
                    comparisons__in=version_comps,
                ).distinct().count()
                versions.append({
                    'id': str(version.pk), 'version_number': version.version_number,
                    'uploaded_by': version.uploaded_by.name if version.uploaded_by else version.uploaded_by_name,
                    'uploaded_at': version.created_at,
                    'row_count': row_count, 'file_name': version.file.name.rsplit('/', 1)[-1],
                    'calculation_warnings': version.calculation_warnings if scope.all else [],
                })
            payload['versions'] = versions
        payload['unresolved_issues'] = [{
            'id': str(issue.pk), 'issue_type': issue.issue_type,
            'serial': issue.serial_normalized, 'status': issue.status,
            'first_period': issue.first_period.strftime('%Y-%m'),
            'last_period': issue.last_period.strftime('%Y-%m'),
            'conclusion': issue.conclusion, 'note': issue.note,
        } for issue in _issue_queryset_for_scope(ReconciliationIssue.objects.filter(
            supplier=task.supplier,
            status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
        ), scope).order_by('first_period')]
        return Response(payload)

    @transaction.atomic
    def post(self, request, pk):
        scope = resolve_user_scope(request.user)
        task = get_object_or_404(
            _task_queryset_for_scope(
                ReconciliationTask.objects.select_for_update(), scope, require_all_comparisons=True,
            ),
            pk=pk,
        )
        if not request.path.endswith('/archive'):
            return Response({'detail': '不支持的操作'}, status=405)
        if task.status == ReconciliationTask.STATUS_ARCHIVED:
            return Response({'detail': '任务已经归档'}, status=400)
        # Archive gate: reject if any diff rows with billing amounts are still pending (no conclusion_type).
        # system_only comparisons have no order_row (no billing amount) and do not block archiving.
        if task.current_version_id:
            pending_count = ReconciliationComparison.objects.filter(
                version_id=task.current_version_id,
                order_row__isnull=False,
            ).exclude(
                result_type=ReconciliationComparison.RESULT_MATCHED,
            ).filter(
                issue__conclusion_type='',
                issue__status__in=[ReconciliationIssue.STATUS_OPEN, ReconciliationIssue.STATUS_NOT_RECURRED],
            ).count()
            if pending_count > 0:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'detail': f'仍有 {pending_count} 条差异未处理'})
        task.status = ReconciliationTask.STATUS_ARCHIVED
        task.archived_by = request.user
        task.archived_by_name = request.user.name
        task.archived_at = timezone.now()
        task.save(update_fields=['status', 'archived_by', 'archived_by_name', 'archived_at', 'updated_at'])
        create_audit_log(request, 'update', 'ReconciliationTask', task.pk,
                         resource_name=f'{task.supplier.name} {task.period:%Y-%m}',
                         description='归档月度租赁对账任务')
        return Response(_task_payload(task))


class ReconciliationIssueView(ReconciliationPermissionView):
    @audit_log(action='update', resource_type='ReconciliationIssue', description_template='更新对账差异处理记录')
    def patch(self, request, pk):
        scope = resolve_user_scope(request.user)
        issue = get_object_or_404(_issue_queryset_for_scope(ReconciliationIssue.objects.all(), scope), pk=pk)
        issue = update_issue(
            issue, request.user,
            status=request.data.get('status'),
            conclusion=request.data.get('conclusion'),
            note=request.data.get('note'),
            conclusion_type=request.data.get('conclusion_type'),
        )
        return Response({
            'id': str(issue.pk), 'status': issue.status,
            'conclusion': issue.conclusion, 'conclusion_type': issue.conclusion_type, 'note': issue.note,
            'handled_by': issue.handled_by.name if issue.handled_by else issue.handled_by_name or None,
            'handled_at': issue.handled_at,
        })

    def get(self, request, pk):
        scope = resolve_user_scope(request.user)
        issue = get_object_or_404(_issue_queryset_for_scope(ReconciliationIssue.objects.all(), scope), pk=pk)
        history = ReconciliationIssueHistory.objects.filter(issue=issue).select_related('user')
        return Response({
            'id': str(issue.pk), 'status': issue.status, 'conclusion': issue.conclusion,
            'note': issue.note,
            'history': [{
                'user': row.user.name if row.user else row.user_name,
                'created_at': row.created_at,
                'old_status': row.old_status, 'new_status': row.new_status,
                'old_conclusion': row.old_conclusion, 'new_conclusion': row.new_conclusion,
                'old_note': row.old_note, 'new_note': row.new_note,
            } for row in history],
        })


class ReconciliationExportView(ReconciliationPermissionView):
    def get_required_operations_any(self, request):
        if request.method == 'GET':
            return ('view_reconciliation',)
        return super().get_required_operations_any(request)

    @audit_log(action='export', resource_type='ReconciliationTask', description_template='导出月度租赁对账结果')
    def get(self, request):
        scope = resolve_user_scope(request.user)
        task = get_object_or_404(
            _task_queryset_for_scope(
                ReconciliationTask.objects.select_related('supplier', 'current_version'), scope,
            ),
            pk=request.query_params.get('task'),
        )
        if request.query_params.get('type') == 'payment':
            return self._export_payment(task, scope)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = '对账结果'
        sheet.append(['结果', '序列号', '订单号', '订单分公司', '系统分公司', '内部编号', '状态', '资产编号', '起租日期', '记账日期', '系统记账天数', '订单记账天数', '月租金', '系统本月金额', '订单本月金额', '处理结论', '备注'])
        if task.current_version:
            rows = _comparison_queryset_for_scope(
                task.current_version.comparisons.select_related('order_row__branch', 'issue').all(), scope,
            )
            visible_issue_ids = set(_issue_queryset_for_scope(
                ReconciliationIssue.objects.filter(pk__in=rows.values('issue_id')),
                scope,
            ).values_list('pk', flat=True))
            for row in rows:
                order = row.order_row
                issue = row.issue if scope.all or row.issue_id in visible_issue_ids else None
                sheet.append([
                    row.get_result_type_display(),
                    order.serial_original if order else row.system_serial_original,
                    order.order_number if order else '', order.supplier_branch_text if order else '',
                    row.system_branch_name, row.internal_code, row.system_status,
                    row.item_code, order.lease_start_date.isoformat() if order else '',
                    order.accounting_date.isoformat() if order else '',
                    order.billing_days if order else '', order.uploaded_billing_days if order else '',
                    str(order.monthly_rent) if order else '', str(order.month_amount) if order else '',
                    str(order.uploaded_month_amount) if order and order.uploaded_month_amount is not None else '',
                    issue.conclusion if issue else '', issue.note if issue else '',
                ])
        if request.query_params.get('type') == 'differences' and sheet.max_row > 1:
            header = [cell.value for cell in sheet[1]]
            result_column = header.index('结果') + 1
            for row_index in range(sheet.max_row, 1, -1):
                if sheet.cell(row_index, result_column).value == '匹配':
                    sheet.delete_rows(row_index)
        output = BytesIO()
        workbook.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="reconciliation-{task.period:%Y-%m}.xlsx"'
        return response

    def _export_payment(self, task, scope):
        summary = build_payment_summary(task, scope)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = '付款明细'
        sheet.append(['序列号', '分公司', '内部编号', '起租日期', '记账日期', '计费天数', '月租金', '本月金额', '计费状态', '结论'])
        for row in summary['rows']:
            sheet.append([
                row['serial'],
                row['branch'],
                row['internal_code'],
                row['lease_start_date'],
                row['accounting_date'],
                row['billing_days'],
                row['monthly_rent'],
                row['month_amount'],
                row['billing_status'],
                row['conclusion_type'],
            ])
        output = BytesIO()
        workbook.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="payment-{task.period:%Y-%m}.xlsx"'
        return response


class BranchSummaryView(ReconciliationPermissionView):
    def get(self, request, pk):
        scope = resolve_user_scope(request.user)
        task = get_object_or_404(
            _task_queryset_for_scope(
                ReconciliationTask.objects.select_related('supplier', 'current_version'),
                scope,
            ),
            pk=pk,
        )
        return Response(build_branch_summary(task, scope))


class RematchView(ReconciliationImportPermissionView):
    @audit_log(action='rematch', resource_type='ReconciliationTask', description_template='重新对账（复用订单数据重跑比对）')
    def post(self, request, pk):
        scope = resolve_user_scope(request.user)
        task = get_object_or_404(
            _task_queryset_for_scope(
                ReconciliationTask.objects.select_related('supplier', 'current_version'),
                scope,
            ),
            pk=pk,
        )
        version_number = rematch_task(task, request.user)
        return Response({'version': version_number})


class PaymentSummaryView(ReconciliationPermissionView):
    def get(self, request, pk):
        scope = resolve_user_scope(request.user)
        task = get_object_or_404(
            _task_queryset_for_scope(
                ReconciliationTask.objects.select_related('supplier', 'current_version'),
                scope,
            ),
            pk=pk,
        )
        return Response(build_payment_summary(task, scope))
