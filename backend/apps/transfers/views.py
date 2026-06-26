import io
from datetime import date
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from core.pagination import StandardPagination
from core.permissions import DataScopeMixin
from apps.permissions.permissions import OperationPermission
from apps.audit.decorators import audit_log
from .models import Transfer
from .serializers import TransferSerializer, TransferActionSerializer, ApproveSerializer
from .filters import TransferFilterSet

# Active inventory statuses that lock a branch's transfers
_INVENTORY_LOCKED_STATUSES = ['in_progress', 'pending_review']


class TransferViewSet(DataScopeMixin, viewsets.ModelViewSet):
    queryset = Transfer.objects.select_related('from_branch', 'to_branch').all()
    serializer_class = TransferSerializer
    filterset_class = TransferFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    # 调拨按「调出 / 调入」双向分公司过滤
    scope_transfer_fields = ('from_branch', 'to_branch')
    # 审批要求 approve_transfer；入库确认要求 manage_assets；其余读写无声明即放行
    required_operations = {
        'approve': 'approve_transfer',
        'warehouse': 'manage_assets',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def _check_inventory_lock(self, branch_name=None, branch_id=None):
        """Raise ValidationError if branch has active inventory tasks."""
        from apps.inventories.models import InventoryTask
        from apps.organizations.models import Branch
        branch = None
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
            except Branch.DoesNotExist:
                return
        elif branch_name:
            try:
                branch = Branch.objects.get(name=branch_name)
            except Branch.DoesNotExist:
                return
        if not branch:
            return
        if InventoryTask.objects.filter(
            branch=branch,
            status__in=_INVENTORY_LOCKED_STATUSES,
        ).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'detail': f'分公司「{branch.name}」正在进行盘点，暂时无法进行此操作',
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

        # Auto-fill FK from CharField if not provided
        from apps.organizations.models import Branch
        from_branch = data.pop('from_branch', None)
        to_branch = data.pop('to_branch', None)

        if not from_branch and data.get('调出分公司'):
            try:
                from_branch = Branch.objects.get(name=data['调出分公司'])
            except Branch.DoesNotExist:
                pass
        if not to_branch and data.get('调入分公司'):
            try:
                to_branch = Branch.objects.get(name=data['调入分公司'])
            except Branch.DoesNotExist:
                pass

        # Check inventory lock on both source and target branches
        self._check_inventory_lock(
            branch_name=data.get('调出分公司', ''),
            branch_id=from_branch.id if from_branch else None,
        )
        self._check_inventory_lock(
            branch_name=data.get('调入分公司', ''),
            branch_id=to_branch.id if to_branch else None,
        )

        transfer = Transfer.objects.create(
            from_branch=from_branch,
            to_branch=to_branch,
            **data,
        )
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
    @audit_log(action='recovery', resource_type='Transfer', description_template='资产回收')
    def recovery(self, request):
        """资产回收"""
        return self._create_action(request, Transfer.ACTION_RECOVERY)

    def _sync_asset(self, transfer):
        """Sync Asset state after transfer approval."""
        from django.db import transaction as tx
        from apps.assets.models import Asset

        sync_map = {
            Transfer.ACTION_ASSIGN: self._sync_assign,
            Transfer.ACTION_RETURN: self._sync_return,
            Transfer.ACTION_TRANSFER: self._sync_transfer,
        }
        handler = sync_map.get(transfer.action_type)
        if not handler:
            return

        with tx.atomic():
            asset = (
                Asset.objects.select_for_update()
                .filter(资产编号=transfer.资产编号)
                .first()
            )
            if asset:
                handler(asset, transfer)

    def _sync_assign(self, asset, transfer):
        asset.当前状态 = '使用中'
        asset.save(update_fields=['当前状态', 'updated_at'])

    def _sync_return(self, asset, transfer):
        asset.当前状态 = '在库'
        asset.save(update_fields=['当前状态', 'updated_at'])

    def _sync_transfer(self, asset, transfer):
        if transfer.to_branch:
            asset.branch = transfer.to_branch
            asset.分公司 = transfer.调入分公司
            asset.分公司编号 = transfer.to_branch.code
        asset.save(update_fields=['branch', '分公司', '分公司编号', 'updated_at'])

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, OperationPermission])
    @audit_log(action='approve', resource_type='Transfer', description_template='审批流转单')
    def approve(self, request, pk=None):
        """审批调拨单（事务内加锁，保证审批与资产同步原子、并发幂等）"""
        from django.db import transaction

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

        with transaction.atomic():
            # 加锁重取，防止并发重复审批导致资产状态被多次同步
            locked = Transfer.objects.select_for_update().get(pk=transfer.pk)
            if locked.审批状态 != '待审批':
                return Response(
                    {'detail': '该记录已审批'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if approved:
                locked.审批状态 = '已通过'
                self._sync_asset(locked)
            else:
                locked.审批状态 = '已驳回'

            locked.审批人 = request.user.name or request.user.phone
            locked.审批时间 = timezone.now()
            if reason:
                locked.备注 = (locked.备注 + '\n' + reason).strip()
            locked.save(update_fields=[
                '审批状态', '审批人', '审批时间', '备注', 'updated_at',
            ])
        return Response(TransferSerializer(locked).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, OperationPermission])
    @audit_log(action='warehouse', resource_type='Transfer', description_template='采购入库确认')
    def warehouse(self, request, pk=None):
        """采购入库确认 - 审批通过后手动入库，更新资产库存"""
        from django.db import transaction
        from django.db.models import F
        from apps.assets.models import Asset
        from datetime import date

        transfer = self.get_object()

        if transfer.action_type != Transfer.ACTION_PURCHASE:
            return Response({'detail': '仅采购入库类型可执行入库操作'}, status=status.HTTP_400_BAD_REQUEST)
        if transfer.审批状态 != '已通过':
            return Response({'detail': '仅已通过的记录可执行入库操作'}, status=status.HTTP_400_BAD_REQUEST)

        branch = transfer.from_branch
        branch_code = branch.code if branch else ''

        with transaction.atomic():
            existing = Asset.objects.select_for_update().filter(资产编号=transfer.资产编号).first()
            if existing:
                Asset.objects.filter(pk=existing.pk).update(
                    数量=F('数量') + transfer.调拨数量,
                    当前状态='在库',
                )
            else:
                max_seq = Asset.objects.order_by('-序号').values_list('序号', flat=True).first() or 0
                Asset.objects.create(
                    序号=max_seq + 1,
                    分公司=transfer.调出分公司,
                    分公司编号=branch_code,
                    branch=branch,
                    资产编号=transfer.资产编号,
                    资产名称=transfer.资产名称,
                    规格=transfer.规格型号,
                    供应商=transfer.供应商 or '',
                    入库日期=date.today(),
                    数量=transfer.调拨数量,
                    单价=transfer.单价,
                    购入金额=transfer.总金额,
                    所属部门=transfer.需求部门 or '',
                    当前状态='在库',
                    备注=transfer.备注 or '',
                )

            transfer.审批状态 = '已入库'
            transfer.save(update_fields=['审批状态', 'updated_at'])

        return Response(TransferSerializer(transfer).data)

    ACTION_TYPE_MAP = {
        '采购入库': Transfer.ACTION_PURCHASE,
        '领用': Transfer.ACTION_ASSIGN,
        '领用出库': Transfer.ACTION_ASSIGN,
        '归还': Transfer.ACTION_RETURN,
        '调拨': Transfer.ACTION_TRANSFER,
        '回收': Transfer.ACTION_RECOVERY,
    }

    TYPE_TEMPLATES = {
        'purchase': {
            'headers': ['采购日期', '分公司', '资产编号', '物品名称', '规格型号', '图片',
                        '供应商', '采购数量', '单价', '总金额', '需求部门', '采购经办人', '备注'],
            'sheet': '采购入库',
            'filename': 'purchase_template.xlsx',
        },
        'assign': {
            'headers': ['分公司', '日期', '领用物品', '领用数量', '用途', '领用部门', '备注'],
            'sheet': '领用出库',
            'filename': 'assign_template.xlsx',
        },
        'transfer': {
            'headers': ['调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
                        '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
                        '调出负责人', '调入负责人', '备注'],
            'sheet': '调拨',
            'filename': 'transfer_template.xlsx',
        },
        'recovery': {
            'headers': ['分公司', '资产编号', '资产类目', '物品分类', '资产名称', '回收分类',
                        '入库日期', '数量', '单位', '规格', '出库日期', '所属部门',
                        '存放位置', '经办人', '备注'],
            'sheet': '回收',
            'filename': 'recovery_template.xlsx',
        },
    }

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        """下载空白导入模板，按 type 参数区分。"""
        import openpyxl
        from django.http import HttpResponse

        template_type = request.query_params.get('type', 'transfer')
        tpl = self.TYPE_TEMPLATES.get(template_type, self.TYPE_TEMPLATES['transfer'])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = tpl['sheet']
        ws.append(tpl['headers'])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{tpl["filename"]}"'
        return response

    @action(detail=False, methods=['get'], url_path='export')
    def export_excel(self, request):
        """导出流转记录 Excel，按 type 参数区分列。"""
        import openpyxl
        from django.http import HttpResponse
        from django.db.models import Count
        from apps.assets.models import Asset

        queryset = self.filter_queryset(self.get_queryset())
        template_type = request.query_params.get('type', 'transfer')

        wb = openpyxl.Workbook()
        ws = wb.active

        if template_type == 'purchase':
            ws.title = '采购入库'
            headers = ['采购日期', '分公司', '资产编号', '物品名称', '规格型号', '图片',
                       '供应商', '采购数量', '单价', '总金额', '需求部门', '采购经办人', '备注']
            ws.append(headers)
            for t in queryset:
                ws.append([
                    str(t.调拨日期) if t.调拨日期 else '',
                    t.调出分公司, t.资产编号, t.资产名称, t.规格型号, '',
                    t.供应商, t.调拨数量, t.单价 or '', t.总金额 or '',
                    t.需求部门, t.采购经办人, t.备注,
                ])

        elif template_type == 'assign':
            ws.title = '领用出库'
            headers = ['分公司', '日期', '领用物品', '领用数量', '用途', '领用部门',
                       '部门累计领用', '当前库存', '是否核对', '备注']
            ws.append(headers)

            asset_codes = list(queryset.values_list('资产编号', flat=True))
            asset_stock_map = dict(
                Asset.objects.filter(资产编号__in=asset_codes).values_list('资产编号', '数量')
            )
            dept_counts = dict(
                Transfer.objects.filter(
                    action_type=Transfer.ACTION_ASSIGN,
                    审批状态__in=['已通过', '已入库'],
                ).values('调出分公司', '调出部门').annotate(cnt=Count('id')).values_list('调出分公司', '调出部门', 'cnt')
            )
            dept_count_map = {(k[0], k[1]): k[2] for k in dept_counts}

            for t in queryset:
                dept_total = dept_count_map.get((t.调出分公司, t.调出部门), 0)
                current_stock = asset_stock_map.get(t.资产编号, 0)
                ws.append([
                    t.调出分公司,
                    str(t.调拨日期) if t.调拨日期 else '',
                    t.资产名称, t.调拨数量, t.用途, t.调出部门,
                    dept_total, current_stock, '待核对', t.备注,
                ])

        elif template_type == 'recovery':
            ws.title = '回收'
            headers = ['序号', '分公司', '资产编号', '资产类目', '物品分类', '资产名称',
                       '回收分类', '入库日期', '数量', '单位', '规格', '出库日期',
                       '所属部门', '当前处理状态', '存放位置', '经办人', '备注']
            ws.append(headers)
            for idx, t in enumerate(queryset, start=1):
                ws.append([
                    idx, t.调出分公司, t.资产编号, t.资产类目, t.物品分类,
                    t.资产名称, t.回收分类,
                    str(t.调拨日期) if t.调拨日期 else '',
                    t.调拨数量, t.单位, t.规格型号,
                    str(t.出库日期) if t.出库日期 else '',
                    t.调出部门, t.审批状态, t.存放位置, t.采购经办人, t.备注,
                ])

        else:
            ws.title = '调拨'
            headers = ['调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
                       '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
                       '调出负责人', '调入负责人', '备注']
            ws.append(headers)
            for t in queryset:
                ws.append([
                    str(t.调拨日期) if t.调拨日期 else '',
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
        response['Content-Disposition'] = (
            f'attachment; filename="{template_type}'
            f'_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        )
        return response

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import')
    def import_excel(self, request):
        """批量导入流转记录，按 type 参数区分列映射。"""
        import openpyxl
        from datetime import datetime as dt

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

        template_type = request.query_params.get('type', 'transfer')

        try:
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
        imported = 0
        errors = []
        creator = request.user.name or request.user.phone

        def _parse_date(val):
            if hasattr(val, 'strftime'):
                return val
            return dt.strptime(str(val).strip(), '%Y-%m-%d').date()

        for i, row in enumerate(rows, start=2):
            try:
                if template_type == 'purchase':
                    Transfer.objects.create(
                        调拨日期=_parse_date(row[0]),
                        action_type=Transfer.ACTION_PURCHASE,
                        调出分公司=str(row[1] or ''),
                        资产编号=str(row[2] or ''),
                        资产名称=str(row[3] or ''),
                        规格型号=str(row[4] or ''),
                        供应商=str(row[6] or ''),
                        调拨数量=int(row[7]) if row[7] else 1,
                        单价=row[8],
                        总金额=row[9],
                        需求部门=str(row[10] or ''),
                        采购经办人=str(row[11] or ''),
                        备注=str(row[12] or ''),
                        审批状态='待审批',
                        创建人=creator,
                    )

                elif template_type == 'assign':
                    Transfer.objects.create(
                        调拨日期=_parse_date(row[1]),
                        action_type=Transfer.ACTION_ASSIGN,
                        调出分公司=str(row[0] or ''),
                        资产名称=str(row[2] or ''),
                        调拨数量=int(row[3]) if row[3] else 1,
                        用途=str(row[4] or ''),
                        调出部门=str(row[5] or ''),
                        备注=str(row[6] or ''),
                        审批状态='待审批',
                        创建人=creator,
                    )

                elif template_type == 'recovery':
                    Transfer.objects.create(
                        调拨日期=_parse_date(row[6]) if row[6] else date.today(),
                        action_type=Transfer.ACTION_RECOVERY,
                        调出分公司=str(row[0] or ''),
                        资产编号=str(row[1] or ''),
                        资产类目=str(row[2] or ''),
                        物品分类=str(row[3] or ''),
                        资产名称=str(row[4] or ''),
                        回收分类=str(row[5] or ''),
                        调拨数量=int(row[7]) if row[7] else 1,
                        单位=str(row[8] or ''),
                        规格型号=str(row[9] or ''),
                        出库日期=_parse_date(row[10]) if row[10] else None,
                        调出部门=str(row[11] or ''),
                        存放位置=str(row[13] or ''),
                        采购经办人=str(row[14] or ''),
                        备注=str(row[15] or ''),
                        审批状态='待审批',
                        创建人=creator,
                    )

                else:  # transfer
                    Transfer.objects.create(
                        调拨日期=_parse_date(row[0]),
                        action_type=Transfer.ACTION_TRANSFER,
                        调出分公司=str(row[1] or ''),
                        调出部门=str(row[2] or ''),
                        调入分公司=str(row[3] or ''),
                        调入部门=str(row[4] or ''),
                        资产编号=str(row[5] or ''),
                        资产名称=str(row[6] or ''),
                        规格型号=str(row[7] or ''),
                        调拨数量=int(row[8]) if row[8] else 1,
                        调拨原因=str(row[9] or ''),
                        调出负责人=str(row[10] or ''),
                        调入负责人=str(row[11] or ''),
                        备注=str(row[12] or ''),
                        审批状态='待审批',
                        创建人=creator,
                    )
                imported += 1
            except Exception as e:
                errors.append(f'第 {i} 行: {str(e)}')

        wb.close()
        return Response({'imported': imported, 'errors': errors})
