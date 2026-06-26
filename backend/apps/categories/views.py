import io
from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from apps.permissions.permissions import OperationPermission
from core.pagination import StandardPagination
from .models import Category
from .serializers import CategorySerializer
from .filters import CategoryFilterSet


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_class = CategoryFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    # 创建/更新/删除/导入需 manage_categories；读取无声明即放行
    required_operations = {
        'create': 'manage_categories',
        'update': 'manage_categories',
        'partial_update': 'manage_categories',
        'destroy': 'manage_categories',
        'import_excel': 'manage_categories',
    }

    def create(self, request, *args, **kwargs):
        """创建分类，处理重复编号错误"""
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except IntegrityError:
            return Response(
                {'asset_code': ['资产编号已存在，请使用其他编号']},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """更新分类，处理重复编号错误"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except IntegrityError:
            return Response(
                {'asset_code': ['资产编号已存在，请使用其他编号']},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='export')
    def export_excel(self, request):
        """导出分类数据为 Excel"""
        import openpyxl

        queryset = self.filter_queryset(self.get_queryset())

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '分类数据'

        headers = ['资产类目', '物品分类', '资产名称', '资产编号', '计量单位', '资产数量', '在库数量', '警戒线', '备注']
        ws.append(headers)

        column_widths = [15, 15, 20, 15, 12, 10, 10, 10, 25]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = width

        for obj in queryset:
            ws.append([
                obj.asset_category,
                obj.item_category,
                obj.asset_name,
                obj.asset_code,
                obj.unit,
                obj.asset_count,
                obj.in_stock_count,
                obj.warning_line or '',
                obj.remarks or '',
            ])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="categories_export.xlsx"'
        return response

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        """下载分类导入 Excel 模板"""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '分类导入模板'

        headers = ['资产类目', '物品分类', '资产名称', '资产编号', '计量单位', '警戒线', '备注']
        ws.append(headers)

        # 设置列宽
        column_widths = [15, 15, 20, 15, 12, 10, 25]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = width

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="category_import_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import')
    def import_excel(self, request):
        """Excel 批量导入分类"""
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
        errors = []

        for i, row in enumerate(rows, start=2):
            try:
                asset_category = str(row[0] or '').strip()
                item_category = str(row[1] or '').strip()
                asset_name = str(row[2] or '').strip()
                asset_code = str(row[3] or '').strip()
                unit = str(row[4] or '').strip()

                if not all([asset_category, item_category, asset_name, asset_code, unit]):
                    errors.append(f'第 {i} 行: 必填字段不能为空')
                    continue

                Category.objects.update_or_create(
                    asset_code=asset_code,
                    defaults={
                        'asset_category': asset_category,
                        'item_category': item_category,
                        'asset_name': asset_name,
                        'unit': unit,
                        'warning_line': int(row[5]) if row[5] else None,
                        'remarks': str(row[6] or ''),
                    },
                )
                imported += 1
            except Exception as e:
                errors.append(f'第 {i} 行: {str(e)}')

        wb.close()
        return Response({'imported': imported, 'errors': errors})
