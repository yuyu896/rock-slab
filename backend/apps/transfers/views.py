import io
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from core.pagination import StandardPagination
from core.permissions import IsRoleMin, CanApprove, DataScopeMixin
from apps.audit.decorators import audit_log
from .models import Transfer
from .serializers import TransferSerializer, TransferActionSerializer, ApproveSerializer
from .filters import TransferFilterSet

# Active inventory statuses that lock a branch's transfers
_INVENTORY_LOCKED_STATUSES = ['in_progress', 'pending_review']


class TransferViewSet(DataScopeMixin, viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    filterset_class = TransferFilterSet
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = StandardPagination
    min_role = 'staff'

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def _check_inventory_lock(self, branch_name):
        """Raise ValidationError if branch has active inventory tasks."""
        if not branch_name:
            return
        from apps.inventories.models import InventoryTask
        from apps.organizations.models import Branch
        try:
            branch = Branch.objects.get(name=branch_name)
        except Branch.DoesNotExist:
            return
        if InventoryTask.objects.filter(
            branch=branch,
            status__in=_INVENTORY_LOCKED_STATUSES,
        ).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'detail': f'分公司「{branch_name}」正在进行盘点，暂时无法进行此操作',
                'code': 'INVENTORY_LOCKED',
            })

    def _create_action(self, request, action_type):
        """Shared helper for the 5 action routes."""
        serializer = TransferActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data['action_type'] = action_type
        if not data.get('创建人'):
            data['创建人'] = request.user.name or request.user.phone

        # Check inventory lock on both source and target branches
        self._check_inventory_lock(data.get('调出分公司', ''))
        self._check_inventory_lock(data.get('调入分公司', ''))

        transfer = Transfer.objects.create(**data)
        return Response(
            TransferSerializer(transfer).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'])
    @audit_log(action='purchase', resource_type='Transfer', description_template='采购入库')
    def purchase(self, request):
        """采购入库"""
        return self._create_action(request, Transfer.ACTION_PURCHASE)

    @action(detail=False, methods=['post'])
    @audit_log(action='assign', resource_type='Transfer', description_template='资产领用')
    def assign(self, request):
        """资产领用"""
        return self._create_action(request, Transfer.ACTION_ASSIGN)

    @action(detail=False, methods=['post'], url_path='return')
    @audit_log(action='return', resource_type='Transfer', description_template='资产归还')
    def return_asset(self, request):
        """资产归还 - mapped as 'return' on the frontend."""
        return self._create_action(request, Transfer.ACTION_RETURN)

    @action(detail=False, methods=['post'])
    @audit_log(action='transfer', resource_type='Transfer', description_template='资产调拨')
    def transfer(self, request):
        """资产调拨"""
        return self._create_action(request, Transfer.ACTION_TRANSFER)

    @action(detail=False, methods=['post'])
    @audit_log(action='repair', resource_type='Transfer', description_template='资产维修')
    def repair(self, request):
        """资产维修"""
        return self._create_action(request, Transfer.ACTION_REPAIR)

    @action(detail=False, methods=['post'])
    @audit_log(action='scrap', resource_type='Transfer', description_template='资产报废')
    def scrap(self, request):
        """资产报废"""
        return self._create_action(request, Transfer.ACTION_SCRAP)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanApprove])
    @audit_log(action='approve', resource_type='Transfer', description_template='审批流转单')
    def approve(self, request, pk=None):
        """审批调拨单"""
        transfer = self.get_object()
        serializer = ApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if transfer.审批状态 != '待审批':
            return Response(
                {'detail': '该记录已审批'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approved = serializer.validated_data['approved']
        reason = serializer.validated_data.get('reason', '')

        if approved:
            transfer.审批状态 = '已通过'
        else:
            transfer.审批状态 = '已驳回'

        transfer.审批人 = request.user.name or request.user.phone
        transfer.审批时间 = timezone.now()
        if reason:
            transfer.备注 = (transfer.备注 + '\n' + reason).strip()
        transfer.save(update_fields=[
            '审批状态', '审批人', '审批时间', '备注', 'updated_at',
        ])
        return Response(TransferSerializer(transfer).data)

    # ---- Batch import / export ----

    ACTION_TYPE_MAP = {
        '采购入库': Transfer.ACTION_PURCHASE,
        '领用': Transfer.ACTION_ASSIGN,
        '领用出库': Transfer.ACTION_ASSIGN,
        '归还': Transfer.ACTION_RETURN,
        '调拨': Transfer.ACTION_TRANSFER,
        '维修': Transfer.ACTION_REPAIR,
        '报废': Transfer.ACTION_SCRAP,
    }

    @action(detail=False, methods=['get'], url_path='export')
    def export_excel(self, request):
        """导出流转记录 Excel / 下载导入模板。"""
        import openpyxl
        from django.http import HttpResponse

        queryset = self.filter_queryset(self.get_queryset())

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '流转记录'

        headers = [
            '调拨日期', '流转类型', '调出分公司', '调出部门', '调入分公司', '调入部门',
            '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
            '调出负责人', '调入负责人', '备注',
        ]
        ws.append(headers)

        for t in queryset:
            action_display = dict(Transfer.ACTION_CHOICES).get(t.action_type, '')
            ws.append([
                str(t.调拨日期) if t.调拨日期 else '',
                action_display,
                t.调出分公司, t.调出部门, t.调入分公司, t.调入部门,
                t.资产编号, t.资产名称, t.规格型号, t.调拨数量,
                t.调拨原因, t.调出负责人, t.调入负责人, t.备注,
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="transfers.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import')
    def import_excel(self, request):
        """批量导入流转记录。"""
        import openpyxl

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wb = openpyxl.load_workbook(file, read_only=True)
            ws = wb.active
        except Exception as e:
            return Response(
                {'detail': f'文件解析失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        imported = 0
        errors = []
        creator = request.user.name or request.user.phone

        for i, row in enumerate(rows, start=2):
            try:
                action_display = str(row[1] or '').strip() if row[1] else ''
                action_type = self.ACTION_TYPE_MAP.get(action_display)
                if not action_type:
                    errors.append(f'第 {i} 行: 流转类型「{action_display}」无法识别，可选值：采购入库/领用出库/归还/调拨/维修/报废')
                    continue

                date_val = row[0]
                if hasattr(date_val, 'strftime'):
                    date_val = date_val
                else:
                    from datetime import datetime
                    date_val = datetime.strptime(str(date_val).strip(), '%Y-%m-%d').date()

                Transfer.objects.create(
                    调拨日期=date_val,
                    action_type=action_type,
                    调出分公司=str(row[2] or ''),
                    调出部门=str(row[3] or ''),
                    调入分公司=str(row[4] or ''),
                    调入部门=str(row[5] or ''),
                    资产编号=str(row[6] or ''),
                    资产名称=str(row[7] or ''),
                    规格型号=str(row[8] or ''),
                    调拨数量=int(row[9]) if row[9] else 1,
                    调拨原因=str(row[10] or ''),
                    调出负责人=str(row[11] or ''),
                    调入负责人=str(row[12] or ''),
                    备注=str(row[13] or ''),
                    审批状态='待审批',
                    创建人=creator,
                )
                imported += 1
            except Exception as e:
                errors.append(f'第 {i} 行: {str(e)}')

        wb.close()
        return Response({'imported': imported, 'errors': errors})
