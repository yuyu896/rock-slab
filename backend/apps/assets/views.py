import io
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from core.pagination import StandardPagination
from core.permissions import IsAdmin, IsRoleMin, DataScopeMixin
from .models import Asset
from .serializers import AssetSerializer
from .filters import AssetFilterSet


class AssetViewSet(DataScopeMixin, viewsets.ReadOnlyModelViewSet):
    """资产管理 - 只读视图，资产信息通过【资产流转】模块的单据流转自动更新。"""
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    filterset_class = AssetFilterSet
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = StandardPagination
    min_role = 'staff'

    def get_queryset(self):
        qs = super().get_queryset()
        return self.get_scoped_queryset(qs)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import',
            permission_classes=[IsAuthenticated, IsRoleMin], min_role='supervisor')
    def import_excel(self, request):
        """Excel batch import via openpyxl."""
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import openpyxl
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

        for i, row in enumerate(rows, start=2):
            try:
                asset_data = {
                    '序号': int(row[0]) if row[0] else 0,
                    '分公司': str(row[1] or ''),
                    '分公司编号': str(row[2] or ''),
                    '资产编号': str(row[3] or ''),
                    '资产类目': str(row[4] or ''),
                    '物品分类': str(row[5] or ''),
                    '资产名称': str(row[6] or ''),
                    '规格': str(row[7] or ''),
                    '供应商': str(row[8] or ''),
                    '入库日期': row[9] if row[9] else None,
                    '是否租用': bool(row[10]) if row[10] else False,
                    '数量': int(row[11]) if row[11] else 1,
                    '单价': row[12] if row[12] else None,
                    '购入金额': row[13] if row[13] else None,
                    '出库日期': row[14] if row[14] else None,
                    '所属部门': str(row[15] or ''),
                    '使用人': str(row[16] or ''),
                    '当前状态': str(row[17] or '在库'),
                    '警戒线': int(row[18]) if row[18] else None,
                    '是否充足': bool(row[19]) if row[19] else True,
                    '电脑序列号': str(row[20] or ''),
                    '备注': str(row[21] or ''),
                }
                Asset.objects.create(**asset_data)
                imported += 1
            except Exception as e:
                errors.append(f'第 {i} 行: {str(e)}')

        wb.close()
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
            '序号', '分公司', '分公司编号', '资产编号', '资产类目',
            '物品分类', '资产名称', '规格', '供应商', '入库日期',
            '是否租用', '数量', '单价', '购入金额', '出库日期',
            '所属部门', '使用人', '当前状态', '警戒线', '是否充足',
            '电脑序列号', '备注',
        ]
        ws.append(headers)

        for asset in queryset:
            ws.append([
                asset.序号, asset.分公司, asset.分公司编号, asset.资产编号,
                asset.资产类目, asset.物品分类, asset.资产名称, asset.规格,
                asset.供应商, str(asset.入库日期) if asset.入库日期 else '',
                asset.是否租用, asset.数量, asset.单价, asset.购入金额,
                str(asset.出库日期) if asset.出库日期 else '',
                asset.所属部门, asset.使用人, asset.当前状态,
                asset.警戒线, asset.是否充足, asset.电脑序列号, asset.备注,
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
