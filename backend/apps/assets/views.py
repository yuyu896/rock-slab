import io
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from core.pagination import StandardPagination
from core.permissions import DataScopeMixin
from apps.permissions.permissions import OperationPermission
from .models import Asset, FixedAsset
from .serializers import AssetSerializer, FixedAssetSerializer
from .filters import AssetFilterSet, FixedAssetFilterSet


class AssetViewSet(DataScopeMixin, viewsets.ModelViewSet):
    """资产管理视图。

    读取：所有登录用户可查看数据范围内的资产（范围由管理授权决定）。
    编辑/删除/导入：需持有 manage_assets 业务操作权限。
    资产信息也通过【资产流转】模块的单据流转自动更新。
    """
    queryset = Asset.objects.select_related('branch').all()
    serializer_class = AssetSerializer
    filterset_class = AssetFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    scope_branch_field = 'branch'
    # 写操作要求 manage_assets；读/导出无声明即放行（范围由 DataScopeMixin 控制）
    required_operations = {
        'update': 'manage_assets',
        'partial_update': 'manage_assets',
        'destroy': 'manage_assets',
        'import_excel': 'manage_assets',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        """下载空白导入模板。"""
        import openpyxl
        from django.http import HttpResponse

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

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="assets_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import',
            permission_classes=[IsAuthenticated, OperationPermission])
    def import_excel(self, request):
        """Excel batch import via openpyxl."""
        from apps.assets.utils.import_helpers import (
            excel_date_to_python, parse_bool_cn, parse_decimal_safe, merge_errors,
        )
        from django.db import IntegrityError

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
        imported = 0
        raw_errors = []

        for i, row in enumerate(rows, start=2):
            row_errors = []

            if not row or not row[2]:
                raw_errors.append((i, '资产编号为空，跳过该行'))
                continue

            asset_code = str(row[2] or '').strip()
            if Asset.objects.filter(资产编号=asset_code).exists():
                raw_errors.append((i, f'资产编号 {asset_code} 已存在，请修改或删除重复行'))
                continue

            # Pre-process fields
            入库日期 = excel_date_to_python(row[10] if len(row) > 10 else None)
            出库日期 = excel_date_to_python(row[16] if len(row) > 16 else None)
            是否租用 = parse_bool_cn(row[11] if len(row) > 11 else None)
            是否充足 = parse_bool_cn(row[21] if len(row) > 21 else '是')

            单价, err = parse_decimal_safe(row[14] if len(row) > 14 else None, '单价')
            if err:
                row_errors.append(err)
            购入金额, err = parse_decimal_safe(row[15] if len(row) > 15 else None, '购入金额')
            if err:
                row_errors.append(err)

            警戒线 = None
            if len(row) > 20 and row[20]:
                try:
                    警戒线 = int(row[20])
                except (ValueError, TypeError):
                    row_errors.append(f'警戒线字段值 "{row[20]}" 不是有效整数')

            数量 = 1
            if len(row) > 12 and row[12]:
                try:
                    数量 = int(row[12])
                except (ValueError, TypeError):
                    row_errors.append(f'数量字段值 "{row[12]}" 不是有效整数')

            if row_errors:
                for e in row_errors:
                    raw_errors.append((i, e))
                continue

            try:
                Asset.objects.create(
                    序号=int(row[0]) if row[0] else 0,
                    分公司=str(row[1] or ''),
                    资产编号=asset_code,
                    分公司编号=str(row[3] or ''),
                    资产类目=str(row[4] or ''),
                    电脑序列号=str(row[5] or ''),
                    供应商=str(row[6] or ''),
                    物品分类=str(row[7] or ''),
                    资产名称=str(row[8] or ''),
                    入库日期=入库日期,
                    是否租用=是否租用,
                    数量=数量,
                    规格=str(row[13] or '') if len(row) > 13 else '',
                    单价=单价,
                    购入金额=购入金额,
                    出库日期=出库日期,
                    所属部门=str(row[17] or '') if len(row) > 17 else '',
                    使用人=str(row[18] or '') if len(row) > 18 else '',
                    当前状态=str(row[19] or '在库') if len(row) > 19 else '在库',
                    警戒线=警戒线,
                    是否充足=是否充足,
                    备注=str(row[22] or '') if len(row) > 22 else '',
                )
                imported += 1
            except IntegrityError:
                raw_errors.append((i, f'资产编号 {asset_code} 已存在'))
            except Exception as e:
                raw_errors.append((i, f'保存失败: {str(e)}'))

        wb.close()
        errors = merge_errors(raw_errors)
        return Response({'imported': imported, 'errors': errors})

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


class FixedAssetViewSet(DataScopeMixin, viewsets.ModelViewSet):
    """固定资产实例管理视图。"""
    queryset = FixedAsset.objects.select_related('asset', 'branch').all()
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
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    def perform_destroy(self, instance):
        instance.delete()

    # 固定资产表 19 列定义（顺序固定）
    FA_HEADERS = [
        '序号', '分公司编号', '分公司', '资产编号', '资产类目',
        '物品分类', '资产名称', '电脑序列号', '供应商', '入库日期',
        '是否租用', '数量', '规格', '单价', '购入金额',
        '出库日期', '所属部门', '使用人', '当前状态',
    ]
    # 只读列（导入时自动继承，无需填写）的索引
    FA_READONLY_COLS = {0, 1, 2, 4, 5, 6, 10, 11, 12, 13, 14, 15}

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.comments import Comment
        from openpyxl.utils import get_column_letter
        from django.http import HttpResponse

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '固定资产实例'
        ws.append(self.FA_HEADERS)

        # 表头样式：加粗、浅绿底、居中、边框
        header_font = Font(bold=True)
        header_fill = PatternFill('solid', fgColor='FFE8F0E8')
        center = Alignment(horizontal='center', vertical='center')
        thin = Side(style='thin')
        border = Border(top=thin, bottom=thin, left=thin, right=thin)

        for col_idx in range(1, len(self.FA_HEADERS) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = border
            # 只读列加批注
            if (col_idx - 1) in self.FA_READONLY_COLS:
                cell.comment = Comment('此列自动继承，无需填写', '系统')

        ws.row_dimensions[1].height = 15
        ws.freeze_panes = 'A2'

        # 自适应列宽（不在数据区创建单元格，避免模板出现空数据行）
        for col_idx, header in enumerate(self.FA_HEADERS, start=1):
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
            asset = inst.asset
            ws.append([
                asset.序号 if asset else '',
                inst.分公司编号,
                inst.分公司,
                inst.资产编号,
                asset.资产类目 if asset else '',
                asset.物品分类 if asset else '',
                asset.资产名称 if asset else '',
                inst.序列号,
                inst.供应商,
                str(inst.入库日期) if inst.入库日期 else '',
                asset.是否租用 if asset else '',
                asset.数量 if asset else '',
                asset.规格 if asset else '',
                asset.单价 if asset else '',
                asset.购入金额 if asset else '',
                str(asset.出库日期) if asset and asset.出库日期 else '',
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
        from apps.assets.utils.import_helpers import excel_date_to_python, merge_errors

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

        if not all_rows:
            return Response({'imported': 0, 'errors': []})

        # 按表头列名建立映射（列顺序无关，兼容用户自定义或简化模板）
        header_row = [str(c or '').strip() for c in all_rows[0]]
        col = {}
        for idx, name in enumerate(header_row):
            if name and name not in col:
                col[name] = idx
        if '序列号' not in col and '电脑序列号' in col:
            col['序列号'] = col['电脑序列号']

        def cell(row, name):
            idx = col.get(name)
            if idx is None or idx >= len(row):
                return ''
            val = row[idx]
            return '' if val is None else val

        imported = 0
        raw_errors = []

        for i, row in enumerate(all_rows[1:], start=2):
            资产编号 = str(cell(row, '资产编号')).strip()
            if not 资产编号:
                raw_errors.append((i, '资产编号为空，跳过该行'))
                continue

            try:
                parent_asset = Asset.objects.get(资产编号=资产编号)
            except Asset.DoesNotExist:
                raw_errors.append((i, f'资产编号 {资产编号} 不存在'))
                continue

            try:
                FixedAsset.objects.create(
                    asset=parent_asset,
                    内部编号=FixedAsset.generate_internal_code(资产编号),
                    资产编号=资产编号,
                    资产名称=str(cell(row, '资产名称')) or parent_asset.资产名称,
                    序列号=str(cell(row, '序列号')),
                    供应商=str(cell(row, '供应商')),
                    入库日期=excel_date_to_python(cell(row, '入库日期') or None),
                    所属部门=str(cell(row, '所属部门')),
                    使用人=str(cell(row, '使用人')),
                    当前状态=str(cell(row, '当前状态') or '在库'),
                    分公司=parent_asset.分公司,
                    分公司编号=parent_asset.分公司编号,
                    branch=parent_asset.branch,
                )
                imported += 1
            except Exception as e:
                raw_errors.append((i, f'保存失败: {str(e)}'))

        errors = merge_errors(raw_errors)
        return Response({'imported': imported, 'errors': errors})
