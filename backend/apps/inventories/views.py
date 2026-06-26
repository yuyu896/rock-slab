from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.pagination import StandardPagination
from core.permissions import DataScopeMixin
from apps.permissions.permissions import OperationPermission
from apps.audit.decorators import audit_log
from .models import InventoryTask, InventoryItem, InventoryCheck
from .serializers import (
    InventoryTaskSerializer,
    InventoryItemSerializer,
    InventoryCheckSerializer,
    CheckItemSerializer,
    RejectSerializer,
    RecountSerializer,
)
from .filters import InventoryTaskFilterSet


class InventoryTaskViewSet(DataScopeMixin, viewsets.ModelViewSet):
    queryset = InventoryTask.objects.select_related(
        'branch', 'category', 'created_by', 'rejected_by',
    ).all()
    serializer_class = InventoryTaskSerializer
    filterset_class = InventoryTaskFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    scope_branch_field = 'branch'
    # 审批 / 驳回要求 approve_inventory
    required_operations = {
        'approve': 'approve_inventory',
        'reject': 'approve_inventory',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # ---- State transition actions ----

    @action(detail=True, methods=['post'])
    @audit_log(action='start', resource_type='InventoryTask', description_template='开始盘点')
    def start(self, request, pk=None):
        """开始盘点: pending -> in_progress"""
        task = self.get_object()
        if not task.can_transition('in_progress'):
            return Response(
                {'detail': f'无法从 {task.get_status_display()} 开始盘点'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check concurrent inventory for same branch
        if task.branch:
            active = InventoryTask.objects.filter(
                branch=task.branch,
                status__in=['in_progress', 'pending_review'],
            ).exclude(pk=task.pk).exists()
            if active:
                return Response(
                    {'detail': f'分公司「{task.branch.name}」已有进行中的盘点任务，不可同时盘点'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        task.status = 'in_progress'
        task.started_at = timezone.now()
        task.save(update_fields=['status', 'started_at', 'updated_at'])

        # Create inventory items from assets in scope
        self._generate_items(task)
        return Response(InventoryTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def check(self, request, pk=None):
        """盘点单项"""
        task = self.get_object()
        if task.status != 'in_progress':
            return Response(
                {'detail': '只有盘点中的任务可以盘点'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CheckItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.assets.models import Asset
        try:
            asset = Asset.objects.get(id=serializer.validated_data['asset_id'])
        except Asset.DoesNotExist:
            return Response(
                {'detail': '资产不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get or create the inventory item
        item, _ = InventoryItem.objects.get_or_create(
            task=task, asset=asset,
            defaults={'expected_qty': asset.数量},
        )

        qty = serializer.validated_data['qty']
        remarks = serializer.validated_data.get('remarks', '')

        # Apply repeat rule
        if task.repeat_rule == 'last':
            item.actual_qty = qty
        else:  # accumulate
            item.actual_qty = (item.actual_qty or 0) + qty

        item.check_count += 1
        item.checked_by = request.user
        item.checked_at = timezone.now()
        item.remarks = remarks

        # Determine result
        if item.actual_qty == item.expected_qty:
            item.result = 'matched'
        elif item.actual_qty > item.expected_qty:
            item.result = 'surplus'
        else:
            item.result = 'missing'
        item.save()

        # Create check record
        check_record = InventoryCheck.objects.create(
            task=task, item=item, asset=asset, qty=qty,
            checked_by=request.user,
        )
        return Response(InventoryCheckSerializer(check_record).data)

    @action(detail=True, methods=['post'])
    @audit_log(action='submit', resource_type='InventoryTask', description_template='提交盘点审核')
    def submit(self, request, pk=None):
        """提交审核: in_progress -> pending_review"""
        task = self.get_object()
        if not task.can_transition('pending_review'):
            return Response(
                {'detail': f'无法从 {task.get_status_display()} 提交审核'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Apply missed rule to unchecked items before submission
        self._apply_missed_rule(task)
        task.status = 'pending_review'
        task.submitted_at = timezone.now()
        task.save(update_fields=['status', 'submitted_at', 'updated_at'])
        return Response(InventoryTaskSerializer(task).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, OperationPermission])
    @audit_log(action='approve', resource_type='InventoryTask', description_template='审批盘点任务')
    def approve(self, request, pk=None):
        """审核通过: pending_review -> completed（事务内调整库存与状态，保证原子）"""
        from django.db import transaction

        task = self.get_object()
        if not task.can_transition('completed'):
            return Response(
                {'detail': f'无法从 {task.get_status_display()} 审核通过'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            # Adjust inventory: update asset quantities based on check results
            self._adjust_inventory(task)
            task.status = 'completed'
            task.completed_at = timezone.now()
            task.save(update_fields=['status', 'completed_at', 'updated_at'])
        return Response(InventoryTaskSerializer(task).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, OperationPermission])
    @audit_log(action='reject', resource_type='InventoryTask', description_template='驳回盘点任务')
    def reject(self, request, pk=None):
        """审核驳回: pending_review -> rejected"""
        task = self.get_object()
        if not task.can_transition('rejected'):
            return Response(
                {'detail': f'无法从 {task.get_status_display()} 驳回'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task.status = 'rejected'
        task.rejected_at = timezone.now()
        task.rejected_by = request.user
        task.reject_reason = serializer.validated_data['reason']
        task.save(update_fields=[
            'status', 'rejected_at', 'rejected_by', 'reject_reason', 'updated_at',
        ])
        return Response(InventoryTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def recount(self, request, pk=None):
        """重新盘点（驳回后）: rejected -> in_progress"""
        task = self.get_object()
        if not task.can_transition('in_progress'):
            return Response(
                {'detail': f'无法从 {task.get_status_display()} 重新盘点'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RecountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_scope = serializer.validated_data.get('reset_scope', 'all')

        task.status = 'in_progress'
        task.save(update_fields=['status', 'updated_at'])

        if reset_scope == 'abnormal_only':
            # Only reset abnormal items (surplus, missing, unchecked)
            task.items.filter(result__in=['surplus', 'missing', 'unchecked']).update(
                actual_qty=None, result='unchecked',
                check_count=0, checked_by=None, checked_at=None,
            )
        else:
            # Reset all items (original behavior)
            task.items.all().update(
                actual_qty=None, result='unchecked',
                check_count=0, checked_by=None, checked_at=None,
            )
        return Response(InventoryTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    @audit_log(action='cancel', resource_type='InventoryTask', description_template='作废盘点任务')
    def cancel(self, request, pk=None):
        """作废: pending/in_progress/rejected -> cancelled"""
        task = self.get_object()
        if not task.can_transition('cancelled'):
            return Response(
                {'detail': f'无法从 {task.get_status_display()} 作废'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = 'cancelled'
        task.save(update_fields=['status', 'updated_at'])
        return Response(InventoryTaskSerializer(task).data)

    # ---- Read-only endpoints ----

    def _build_progress_data(self, task, items=None):
        """Build progress stats dict with rates."""
        if items is None:
            items = task.items.all()
        total = items.count()
        checked = items.filter(result__in=['matched', 'surplus', 'missing']).count()
        matched = items.filter(result='matched').count()
        surplus = items.filter(result='surplus').count()
        missing = items.filter(result='missing').count()
        unchecked = items.filter(result='unchecked').count()
        return {
            'totalItems': total,
            'checkedItems': checked,
            'matchedCount': matched,
            'surplusCount': surplus,
            'missingCount': missing,
            'uncheckedCount': unchecked,
            'matchRate': round(matched / checked * 100, 1) if checked else 0,
            'surplusRate': round(surplus / checked * 100, 1) if checked else 0,
            'missingRate': round(missing / checked * 100, 1) if checked else 0,
        }

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """盘点进度"""
        task = self.get_object()
        return Response(self._build_progress_data(task))

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """盘点报告"""
        task = self.get_object()
        items = task.items.select_related('asset').all()
        data = {
            'task': InventoryTaskSerializer(task).data,
            'progress': self._build_progress_data(task, items),
            'items': InventoryItemSerializer(items, many=True).data,
        }
        return Response(data)

    @action(detail=True, methods=['get'])
    def checks(self, request, pk=None):
        """盘点记录（多人协作）"""
        task = self.get_object()
        queryset = task.checks.select_related('asset', 'checked_by').all()

        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = InventoryCheckSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = InventoryCheckSerializer(queryset, many=True)
        return Response(serializer.data)

    # ---- Excel import/export ----

    @action(detail=True, methods=['get'], url_path='import-template')
    def download_template(self, request, pk=None):
        """下载盘点模板 Excel"""
        import io
        import openpyxl
        from django.http import HttpResponse

        task = self.get_object()
        items = task.items.select_related('asset').order_by('created_at')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '盘点表'
        ws.append(['序号', '资产编号', '资产名称', '资产类目', '账面数量', '实盘数量', '备注'])

        for idx, item in enumerate(items, start=1):
            asset = item.asset
            ws.append([
                idx,
                asset.资产编号,
                asset.资产名称,
                asset.资产类目,
                item.expected_qty,
                '',  # 实盘数量 - 用户填写
                '',  # 备注 - 用户填写
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        filename = f'盘点表_{task.name}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'], url_path='import-result',
            parser_classes=[MultiPartParser])
    def import_result(self, request, pk=None):
        """导入盘点结果 Excel"""
        task = self.get_object()
        if task.status != 'in_progress':
            return Response(
                {'detail': '只有盘点中的任务可以导入'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)

        from core.upload_validation import (
            validate_excel_upload, validate_row_count, UploadValidationError,
        )
        try:
            validate_excel_upload(file)
        except UploadValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file, read_only=True)
            ws = wb.active
        except Exception as e:
            return Response(
                {'detail': f'文件解析失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_row_count(ws)
        except UploadValidationError as e:
            wb.close()
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        wb.close()

        imported = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            if not row or not row[1]:
                continue
            asset_code = str(row[1]).strip()
            actual_qty_raw = row[5] if len(row) > 5 else None
            remarks = str(row[6]).strip() if len(row) > 6 and row[6] else ''

            if actual_qty_raw is None:
                continue

            try:
                actual_qty = int(float(str(actual_qty_raw)))
            except (ValueError, TypeError):
                errors.append(f'第 {i} 行: 实盘数量格式错误 "{actual_qty_raw}"')
                continue

            # Find the inventory item by asset code
            try:
                item = task.items.select_related('asset').get(asset__资产编号=asset_code)
            except InventoryItem.DoesNotExist:
                errors.append(f'第 {i} 行: 资产编号 "{asset_code}" 不在盘点范围内')
                continue

            # Apply repeat rule
            if task.repeat_rule == 'last':
                item.actual_qty = actual_qty
            else:  # accumulate
                item.actual_qty = (item.actual_qty or 0) + actual_qty

            item.check_count += 1
            item.checked_by = request.user
            item.checked_at = timezone.now()
            if remarks:
                item.remarks = remarks

            # Determine result
            if item.actual_qty == item.expected_qty:
                item.result = 'matched'
            elif item.actual_qty > item.expected_qty:
                item.result = 'surplus'
            else:
                item.result = 'missing'
            item.save()

            # Create check record
            InventoryCheck.objects.create(
                task=task, item=item, asset=item.asset, qty=actual_qty,
                checked_by=request.user,
            )
            imported += 1

        return Response({
            'imported': imported,
            'errors': errors,
        })

    # ---- Helpers ----

    def _generate_items(self, task):
        """Generate inventory items from assets matching the task scope."""
        from apps.assets.models import Asset
        qs = Asset.objects.all()
        if task.branch:
            qs = qs.filter(分公司编号=task.branch.code)
        if task.category:
            qs = qs.filter(资产类目=task.category.asset_category)
        for asset in qs:
            InventoryItem.objects.get_or_create(
                task=task, asset=asset,
                defaults={'expected_qty': asset.数量},
            )

    def _apply_missed_rule(self, task):
        """Apply missed rule to unchecked items before submission."""
        unchecked_items = task.items.filter(result='unchecked')
        if task.missed_rule == 'zero':
            # Zero out: set actual_qty to 0 and result to 'missing'
            unchecked_items.update(actual_qty=0, result='missing')
        # 'keep' rule: leave unchecked items as-is (no change needed)

    def _adjust_inventory(self, task):
        """Adjust asset quantities based on inventory check results.

        在事务内对每个资产行 select_for_update 加锁后再更新，防止与
        采购入库/调拨等并发操作产生丢失更新。
        """
        from django.db import transaction
        from apps.assets.models import Asset

        items = task.items.select_related('asset').exclude(result='unchecked')
        with transaction.atomic():
            for item in items:
                if item.actual_qty is not None and item.actual_qty != item.expected_qty:
                    diff = item.actual_qty - item.expected_qty
                    asset = Asset.objects.select_for_update().get(pk=item.asset_id)
                    asset.数量 = max(0, asset.数量 + diff)
                    asset.save(update_fields=['数量', 'updated_at'])
