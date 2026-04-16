## 1. 后端导出端点

- [x] 1.1 在 `backend/apps/categories/views.py` 的 CategoryViewSet 中新增 `@action(detail=False, methods=['get'], url_path='export')` 方法 `export_excel`
- [x] 1.2 使用 `self.filter_queryset(self.get_queryset())` 获取筛选后的数据集
- [x] 1.3 使用 openpyxl 创建 Workbook，写入表头行（资产类目、物品分类、资产名称、资产编号、计量单位、资产数量、在库数量、警戒线、备注）和逐行数据
- [x] 1.4 返回 HttpResponse，Content-Type 为 xlsx，Content-Disposition 为 attachment，文件名 `分类数据导出.xlsx`

## 2. 前端 API 函数

- [x] 2.1 在 `frontend/src/api/categories.ts` 中新增 `exportCategories(params?)` 函数，构建带筛选参数的 URL 并触发下载

## 3. 前端导出按钮

- [x] 3.1 在 `frontend/src/views/Category.vue` 页面头部 `.header-actions` 区域中"导入"按钮前新增"导出"按钮
- [x] 3.2 按钮点击时调用 `exportCategories`，传入当前筛选条件（`filterCategory`、`filterKeyword`）

## 4. 验证

- [x] 4.1 测试 `GET /api/categories/export/` 返回完整 xlsx 文件
- [x] 4.2 测试带筛选参数导出，验证只包含筛选后的数据
- [x] 4.3 验证前端"导出"按钮点击后浏览器下载文件
