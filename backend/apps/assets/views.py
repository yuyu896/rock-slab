import io
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from core.pagination import StandardPagination
from core.permissions import DataScopeMixin
from apps.permissions.permissions import OperationPermission
from rest_framework.exceptions import ValidationError
from .models import Asset, AssetStock, FixedAsset, LedgerAdjustment
from .serializers import (
    AssetSerializer,
    AssetStockSerializer,
    FixedAssetSerializer,
    LedgerAdjustmentSerializer,
)
from .filters import AssetFilterSet, AssetStockFilterSet, FixedAssetFilterSet


def _batch_delete(viewset, request):
    """批量删除：按数据范围过滤后删除指定 ids，返回实际删除数（越权 id 自动排除）。"""
    ids = request.data.get('ids') or []
    if not isinstance(ids, list) or not ids:
        return Response(
            {'detail': '请提供要删除的 id 列表'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    count, _ = viewset.get_queryset().filter(id__in=ids).delete()
    return Response({'deleted': count})


class AssetViewSet(DataScopeMixin, viewsets.ModelViewSet):
    """资产明细视图 —— P1 冻结只读（历史视图，P2 物理退役）。

    库存事实唯一存放于台账（AssetStock），Asset 不再被任何流转/盘点/导入写入；
    写接口全部下线：增删改 405，导入 410（改走台账增量导入）。
    """
    queryset = Asset.objects.select_related('branch').all()
    serializer_class = AssetSerializer
    filterset_class = AssetFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    scope_branch_field = 'branch'

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def _frozen(self, request):
        return Response(
            {'detail': '资产明细已冻结为历史视图（P2 退役），数量变动请经流转单/调整单'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def create(self, request, *args, **kwargs):
        return self._frozen(request)

    def update(self, request, *args, **kwargs):
        return self._frozen(request)

    def partial_update(self, request, *args, **kwargs):
        return self._frozen(request)

    def destroy(self, request, *args, **kwargs):
        return self._frozen(request)

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        return self._frozen(request)

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        """下载空白导入模板。"""
        import openpyxl
        from django.http import HttpResponse

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '资产列表'

        headers = [
            '分公司', '资产编号', '资产类目',
            '物品分类', '资产名称', '入库日期', '是否租用',
            '数量', '规格', '单价', '购入金额',
            '出库日期', '所属部门', '当前状态', '备注',
        ]
        ws.append(headers)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="assets_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import')
    def import_excel(self, request):
        """资产明细导入已下线（冻结只读）：改走台账增量导入（生成调整单）。"""
        return Response(
            {'detail': '资产明细导入已下线（表已冻结），请使用台账增量导入（经调整单入账）'},
            status=status.HTTP_410_GONE,
        )

    @action(detail=False, methods=['get'], url_path='export')
    def export_excel(self, request):
        """Excel export via openpyxl."""
        import openpyxl
        from django.http import HttpResponse

        queryset = self.filter_queryset(self.get_queryset())

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '资产列表'

        headers = [
            '序号', '分公司', '资产编号', '分公司编号', '资产类目',
            '电脑序列号', '供应商', '物品分类', '资产名称', '图片',
            '入库日期', '是否租用', '数量', '规格', '单价',
            '购入金额', '出库日期', '所属部门', '使用人', '当前状态',
            '警戒线', '是否充足', '备注',
        ]
        ws.append(headers)

        for asset in queryset:
            ws.append([
                asset.序号, asset.分公司, asset.资产编号, asset.分公司编号,
                asset.资产类目, asset.电脑序列号, asset.供应商,
                asset.物品分类, asset.资产名称,
                asset.图片.url if hasattr(asset, '图片') and asset.图片 else '',
                str(asset.入库日期) if asset.入库日期 else '',
                asset.是否租用, asset.数量, asset.规格, asset.单价,
                asset.购入金额,
                str(asset.出库日期) if asset.出库日期 else '',
                asset.所属部门, asset.使用人, asset.当前状态,
                asset.警戒线, asset.是否充足, asset.备注,
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="assets.xlsx"'
        return response


class AssetStockViewSet(DataScopeMixin, viewsets.ModelViewSet):
    """资产汇总台账 —— 库存唯一事实源（只读 + 增量导入）。

    行级写接口（新增/编辑/删除/批量删除）已下线：数量变动唯一通道是流转单与
    调整单（铁律 2）。导入为两段式增量：默认出差异预览，confirm=1 时按差异
    逐行生成调整单（事由=导入调整）入账。
    """

    queryset = AssetStock.objects.select_related('branch', 'item').all()
    serializer_class = AssetStockSerializer
    filterset_class = AssetStockFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    scope_branch_field = 'branch'
    # 导入权限在 import_excel 内校验（manage_assets 或 adjust_ledger 任一）

    # 台账增量导入模板 3 列：分公司 / 资产编号 / 在库数量
    STOCK_TEMPLATE_HEADERS = ['分公司', '资产编号', '在库数量']

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    # ---- 行级写接口下线（铁律 2：数量变动须经单据） ----

    def _write_disabled(self, request):
        return Response(
            {'detail': '台账为库存唯一事实源，数量变动须经流转单或调整单'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def create(self, request, *args, **kwargs):
        return self._write_disabled(request)

    def update(self, request, *args, **kwargs):
        return self._write_disabled(request)

    def partial_update(self, request, *args, **kwargs):
        return self._write_disabled(request)

    def destroy(self, request, *args, **kwargs):
        return self._write_disabled(request)

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        return self._write_disabled(request)

    # ---- 模板 / 导入 / 导出 ----

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        """下载台账增量导入模板（分公司 / 资产编号 / 在库数量）。"""
        import openpyxl
        from django.http import HttpResponse

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '资产汇总'
        ws.append(self.STOCK_TEMPLATE_HEADERS)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="asset_summary_template.xlsx"'
        return response

    def _parse_import_rows(self, file):
        """解析增量导入文件 → (diffs, errors)。diffs 元素含 branch/item ORM 对象。"""
        from apps.categories.models import Category
        from apps.categories.views import suggest_similar_codes
        from apps.organizations.models import Branch

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file, read_only=True)
            ws = wb.active
        except Exception as e:
            raise ValueError(f'文件解析失败: {str(e)}')

        all_rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not all_rows:
            return [], []

        header_row = [str(c or '').strip() for c in all_rows[0]]
        col = {}
        for idx, name in enumerate(header_row):
            if name and name not in col:
                col[name] = idx

        def cell(row, name):
            idx = col.get(name)
            if idx is None or idx >= len(row):
                return ''
            val = row[idx]
            return '' if val is None else val

        diffs = []
        errors = []
        seen_keys = set()
        branch_map = {b.name: b for b in Branch.objects.all()}
        item_map = {c.asset_code: c for c in Category.objects.all()}

        for i, row in enumerate(all_rows[1:], start=2):
            asset_code = str(cell(row, '资产编号')).strip()
            branch_name = str(cell(row, '分公司')).strip()
            if not asset_code and not branch_name:
                continue
            if not asset_code:
                errors.append(f'第 {i} 行: 资产编号为空')
                continue
            item = item_map.get(asset_code)
            if item is None:
                similar = suggest_similar_codes(asset_code)
                hint = f'，是否想找：{"、".join(similar)}' if similar else ''
                errors.append(f'第 {i} 行: 资产编号 {asset_code} 未在品目字典登记{hint}')
                continue
            branch = branch_map.get(branch_name)
            if branch is None:
                errors.append(f'第 {i} 行: 分公司「{branch_name}」不存在')
                continue
            key = (branch_name, asset_code)
            if key in seen_keys:
                errors.append(f'第 {i} 行: 资产编号 {asset_code} 在文件内重复')
                continue
            seen_keys.add(key)

            qty_raw = cell(row, '在库数量')
            try:
                target_qty = int(qty_raw)
            except (ValueError, TypeError):
                errors.append(f'第 {i} 行: 在库数量 "{qty_raw}" 不是有效整数')
                continue

            current = AssetStock.objects.filter(branch=branch, item=item).first()
            current_qty = current.在库数量 if current else 0
            delta = target_qty - current_qty
            if delta != 0:
                diffs.append({
                    'row': i,
                    'branch': branch,
                    'branch_name': branch_name,
                    'item': item,
                    '资产编号': asset_code,
                    '资产名称': item.asset_name,
                    '现值': current_qty,
                    '导入值': target_qty,
                    '变动量': delta,
                })
        return diffs, errors

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import')
    def import_excel(self, request):
        """台账增量导入：默认返回差异预览；confirm=1 时逐差异生成调整单。"""
        from core.upload_validation import validate_excel_upload, UploadValidationError

        if not (request.user.can('adjust_ledger') or request.user.can('manage_assets')):
            return Response(
                {'detail': '台账导入需要台账调整或资产管理权限'},
                status=status.HTTP_403_FORBIDDEN,
            )

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_excel_upload(file)
        except UploadValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            diffs, errors = self._parse_import_rows(file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if str(request.data.get('confirm')) in ('1', 'true', 'True'):
            from .services import ledger
            applied = 0
            for d in diffs:
                ledger.apply_adjustment(
                    branch=d['branch'],
                    item=d['item'],
                    column=ledger.COLUMN_STOCK,
                    delta=d['变动量'],
                    reason=f'导入调整（在库 {d["现值"]} → {d["导入值"]}）',
                    operator=request.user,
                )
                applied += 1
            return Response({'applied': applied, 'errors': errors})

        return Response({
            'diffs': [
                {
                    '行号': d['row'],
                    '分公司': d['branch_name'],
                    '资产编号': d['资产编号'],
                    '资产名称': d['资产名称'],
                    '现值': d['现值'],
                    '导入值': d['导入值'],
                    '变动量': d['变动量'],
                }
                for d in diffs
            ],
            'errors': errors,
        })

    @action(detail=False, methods=['get'], url_path='export')
    def export_excel(self, request):
        """台账导出（列同页面表头，序号为行号）。"""
        import openpyxl
        from django.http import HttpResponse

        queryset = self.filter_queryset(self.get_queryset())

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '资产汇总'

        headers = [
            '序号', '分公司', '资产编号', '资产名称', '规格', '资产类目', '物品分类',
            '管理方式', '在库数量', '在用数量', '回收库数量', '总量', '警戒线', '是否充足',
        ]
        ws.append(headers)

        for idx, stock in enumerate(queryset, start=1):
            ws.append([
                idx,
                stock.branch.name,
                stock.item.asset_code,
                stock.item.asset_name,
                stock.item.specification,
                stock.item.asset_category,
                stock.item.item_category,
                stock.item.get_management_type_display(),
                stock.在库数量,
                stock.在用数量,
                stock.回收库数量,
                stock.总量,
                stock.生效警戒线 if stock.生效警戒线 is not None else '',
                '是' if stock.是否充足 else '否',
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="asset_summary.xlsx"'
        return response


class LedgerAdjustmentViewSet(DataScopeMixin, viewsets.ReadOnlyModelViewSet):
    """台账调整单：创建即生效（走 ledger service 唯一写入口），列表按范围可读。"""

    queryset = LedgerAdjustment.objects.select_related('branch', 'item', '经办人').all()
    serializer_class = LedgerAdjustmentSerializer
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    scope_branch_field = 'branch'
    required_operations = {
        'create': 'adjust_ledger',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def create(self, request, *args, **kwargs):
        from .services import ledger
        from apps.categories.models import Category
        from apps.organizations.models import Branch

        branch_id = request.data.get('branch')
        asset_code = (request.data.get('资产编号') or '').strip()
        column = request.data.get('目标列')
        reason = (request.data.get('事由') or '').strip()
        try:
            delta = int(request.data.get('变动量'))
        except (ValueError, TypeError):
            return Response({'detail': '变动量必须是整数'}, status=status.HTTP_400_BAD_REQUEST)

        branch = Branch.objects.filter(id=branch_id).first() if branch_id else None
        if branch is None:
            branch_name = (request.data.get('分公司') or '').strip()
            branch = Branch.objects.filter(name=branch_name).first() if branch_name else None
        if branch is None:
            return Response({'detail': '分公司无效'}, status=status.HTTP_400_BAD_REQUEST)
        item = Category.objects.filter(asset_code=asset_code).first() if asset_code else None
        if item is None:
            return Response(
                {'detail': f'资产编号 {asset_code} 未在品目字典登记'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not reason:
            return Response({'detail': '事由不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            adjustment = ledger.apply_adjustment(
                branch=branch,
                item=item,
                column=column,
                delta=delta,
                reason=reason,
                operator=request.user,
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(adjustment).data, status=status.HTTP_201_CREATED)


class FixedAssetViewSet(DataScopeMixin, viewsets.ModelViewSet):
    """固定资产实例管理视图。"""
    queryset = FixedAsset.objects.select_related('branch').all()
    serializer_class = FixedAssetSerializer
    filterset_class = FixedAssetFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    scope_branch_field = 'branch'
    required_operations = {
        'create': 'manage_assets',
        'update': 'manage_assets',
        'partial_update': 'manage_assets',
        'destroy': 'manage_assets',
        'import_excel': 'manage_assets',
        'batch_delete': 'manage_assets',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除固定资产（受数据范围与 manage_assets 权限约束）。"""
        return _batch_delete(self, request)

    # 固定资产表 19 列定义（顺序固定）——用于导出
    FA_HEADERS = [
        '序号', '分公司编号', '分公司', '资产编号', '资产类目',
        '物品分类', '资产名称', '电脑序列号', '供应商', '入库日期',
        '是否租用', '数量', '规格', '单价', '购入金额',
        '出库日期', '所属部门', '使用人', '当前状态',
    ]
    # 导入模板仅含用户填写列（其余导入时自动继承自父资产）
    FA_TEMPLATE_HEADERS = [
        '分公司', '资产编号', '分公司编号', '电脑序列号', '供应商',
        '物品分类', '资产名称', '入库日期', '是否租用', '数量',
        '规格', '单价', '购入金额', '出库日期',
        '所属部门', '使用人', '当前状态', '备注',
    ]

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from django.http import HttpResponse

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '固定资产实例'
        ws.append(self.FA_TEMPLATE_HEADERS)

        # 表头样式：加粗、浅绿底、居中、边框
        header_font = Font(bold=True)
        header_fill = PatternFill('solid', fgColor='FFE8F0E8')
        center = Alignment(horizontal='center', vertical='center')
        thin = Side(style='thin')
        border = Border(top=thin, bottom=thin, left=thin, right=thin)

        for col_idx in range(1, len(self.FA_TEMPLATE_HEADERS) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = border

        ws.row_dimensions[1].height = 15
        ws.freeze_panes = 'A2'

        # 自适应列宽（不在数据区创建单元格，避免模板出现空数据行）
        for col_idx, header in enumerate(self.FA_TEMPLATE_HEADERS, start=1):
            width = max(len(header) * 2.2 + 2, 10)
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="fixed_assets_template.xlsx"'
        return response

    @action(detail=False, methods=['get'], url_path='export')
    def export_excel(self, request):
        """固定资产表导出 19 列。"""
        import openpyxl
        from django.http import HttpResponse

        queryset = self.filter_queryset(self.get_queryset())

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '固定资产表'
        ws.append(self.FA_HEADERS)

        for inst in queryset:
            ws.append([
                '',
                inst.分公司编号,
                inst.分公司,
                inst.资产编号,
                inst.资产类目,
                inst.物品分类,
                inst.资产名称,
                inst.序列号,
                inst.供应商,
                str(inst.入库日期) if inst.入库日期 else '',
                inst.是否租用,
                inst.数量,
                inst.规格,
                inst.单价 or '',
                inst.购入金额 or '',
                str(inst.出库日期) if inst.出库日期 else '',
                inst.所属部门,
                inst.使用人,
                inst.当前状态,
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="fixed_assets.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import',
            permission_classes=[IsAuthenticated, OperationPermission])
    def import_excel(self, request):
        from apps.assets.utils.import_helpers import (
            excel_date_to_python, parse_bool_cn, parse_decimal_safe, merge_errors,
        )
        from apps.organizations.models import Branch
        from apps.organizations.utils import get_branch_name_set, branch_validation_error
        from apps.categories.models import Category

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

        all_rows = list(ws.iter_rows(values_only=True))
        wb.close()

        if len(all_rows) > 201:
            return Response(
                {'detail': f'数据量过大（{len(all_rows) - 1} 行），建议分批导入（每次不超过 200 行）'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not all_rows:
            return Response({'imported': 0, 'errors': []})

        # 按表头列名建立映射（列顺序无关，兼容用户自定义或简化模板）
        header_row = [str(c or '').strip() for c in all_rows[0]]

        # 校验表头与模板一致（列名集合相同，顺序不限）
        template_set = set(self.FA_TEMPLATE_HEADERS)
        uploaded_set = set(h for h in header_row if h)
        if uploaded_set != template_set:
            missing = sorted(template_set - uploaded_set)
            extra = sorted(uploaded_set - template_set)
            parts = []
            if missing:
                parts.append(f'缺少：{"、".join(missing)}')
            if extra:
                parts.append(f'多余：{"、".join(extra)}')
            return Response(
                {'detail': f'表头与模板不一致（{"；".join(parts)}）'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        col = {}
        for idx, name in enumerate(header_row):
            if name and name not in col:
                col[name] = idx
        if '序列号' not in col and '电脑序列号' in col:
            col['序列号'] = col['电脑序列号']
        if '电脑序列号' not in col and '序列号' in col:
            col['电脑序列号'] = col['序列号']

        def cell(row, name):
            idx = col.get(name)
            if idx is None or idx >= len(row):
                return ''
            val = row[idx]
            return '' if val is None else val

        imported = 0
        raw_errors = []
        seen_fa_keys = set()  # 表内去重：(分公司, 分公司编号, 电脑序列号, 所属部门)
        valid_branches = get_branch_name_set()
        # 预加载 DB 已有四元组（防止重复导入）
        existing_fa_keys = set()
        for fa in FixedAsset.objects.values_list('分公司', '分公司编号', '序列号', '所属部门'):
            existing_fa_keys.add(tuple(str(v or '').strip() for v in fa))
        # 预加载每个资产编号的最大内部编号后缀（用 max 后缀而非 count，避免删除/失败导入后序号空洞）
        import re
        from collections import defaultdict
        fa_seq = defaultdict(int)
        for code, inner_code in FixedAsset.objects.values_list('资产编号', '内部编号'):
            match = re.search(r'-(\d+)$', inner_code or '')
            if match:
                seq = int(match.group(1))
                if seq > fa_seq[code]:
                    fa_seq[code] = seq

        for i, row in enumerate(all_rows[1:], start=2):
            资产编号 = str(cell(row, '资产编号')).strip()
            if not 资产编号:
                raw_errors.append((i, '资产编号为空，跳过该行'))
                continue

            # 校验资产编号存在于品目（Category），不再关联资产库存
            category = Category.objects.filter(asset_code=资产编号).first()
            if not category:
                raw_errors.append((i, f'资产编号 {资产编号} 未在品目登记'))
                continue

            分公司 = str(cell(row, '分公司')).strip()
            branch_err = branch_validation_error(分公司, '分公司', valid_branches)
            if branch_err:
                raw_errors.append((i, branch_err))
                continue

            分公司编号 = str(cell(row, '分公司编号')).strip()
            if not 分公司编号:
                raw_errors.append((i, '分公司编号为空，请填写'))
                continue
            电脑序列号 = str(cell(row, '电脑序列号')).strip()
            if not 电脑序列号:
                raw_errors.append((i, '电脑序列号为空，请填写'))
                continue
            所属部门_val = str(cell(row, '所属部门')).strip()
            使用人_val = str(cell(row, '使用人')).strip()

            # 表内去重 + DB 级去重：分公司 + 分公司编号 + 电脑序列号 + 所属部门
            fa_key = (分公司, 分公司编号, 电脑序列号, 所属部门_val)
            if fa_key in seen_fa_keys:
                raw_errors.append((i, f'资产编号 {资产编号} 重复'))
                continue
            if fa_key in existing_fa_keys:
                raw_errors.append((i, f'该行数据已存在（分公司+编号+序列号+部门重复），跳过'))
                continue
            seen_fa_keys.add(fa_key)
            existing_fa_keys.add(fa_key)

            # branch FK 按分公司名称解析（分公司编号是资产内部编号，不是组织编码）
            fa_branch = Branch.objects.filter(name=分公司).first() if 分公司 else None

            try:
                数量 = int(cell(row, '数量')) if cell(row, '数量') else 1
            except (ValueError, TypeError):
                数量 = 1
            单价, _ = parse_decimal_safe(cell(row, '单价'), '单价')
            购入金额, _ = parse_decimal_safe(cell(row, '购入金额'), '购入金额')

            # 内存递增序号（避免同编号多行 count 不更新导致内部编号重复）
            fa_seq[资产编号] += 1
            内部编号 = f'{资产编号}-{fa_seq[资产编号]}'

            try:
                FixedAsset.objects.create(
                    内部编号=内部编号,
                    资产编号=资产编号,
                    资产类目=str(cell(row, '资产类目')) or category.asset_category,
                    资产名称=str(cell(row, '资产名称')) or category.asset_name,
                    序列号=电脑序列号,
                    供应商=str(cell(row, '供应商')),
                    物品分类=str(cell(row, '物品分类')) or category.item_category,
                    入库日期=excel_date_to_python(cell(row, '入库日期') or None),
                    是否租用=parse_bool_cn(cell(row, '是否租用')),
                    数量=数量,
                    规格=str(cell(row, '规格')),
                    单价=单价,
                    购入金额=购入金额,
                    出库日期=excel_date_to_python(cell(row, '出库日期') or None),
                    所属部门=str(cell(row, '所属部门')),
                    使用人=str(cell(row, '使用人')),
                    当前状态=str(cell(row, '当前状态') or '在库'),
                    分公司=分公司,
                    分公司编号=分公司编号,
                    branch=fa_branch,
                    备注=str(cell(row, '备注')),
                )
                imported += 1
            except Exception as e:
                raw_errors.append((i, f'保存失败: {str(e)}'))

        errors = merge_errors(raw_errors)
        return Response({'imported': imported, 'errors': errors})
