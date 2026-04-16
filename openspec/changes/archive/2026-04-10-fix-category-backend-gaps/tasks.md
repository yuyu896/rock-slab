## 1. Category 模型：新增 attribute_template 字段

- [x] 1.1 在 `backend/apps/categories/models.py` 的 Category 模型中新增 `attribute_template = models.JSONField('属性模板', default=dict, blank=True)`
- [x] 1.2 运行 `python manage.py makemigrations categories` 生成迁移文件
- [x] 1.3 运行 `python manage.py migrate` 应用迁移

## 2. Serializer：attribute_template 读写支持

- [x] 2.1 在 `backend/apps/categories/serializers.py` 中新增 `attribute_template` 字段映射（读字段用中文名 `属性模板` source='attribute_template'，写字段保留英文名）
- [x] 2.2 新增 `validate_attribute_template` 方法：校验值为数组或对象格式，数组中每项应含 name 和 type 字段
- [x] 2.3 确保 `attribute_template` 不在 `read_only_fields` 中，允许写入

## 3. ViewSet：Excel 模板下载端点

- [x] 3.1 在 `backend/apps/categories/views.py` 的 CategoryViewSet 中新增 `@action(detail=False, methods=['get'], url_path='template')` 方法
- [x] 3.2 使用 openpyxl 在内存中创建 Workbook，写入表头行（资产类目、物品分类、资产名称、资产编号、计量单位、警戒线、备注）
- [x] 3.3 返回 HttpResponse，Content-Type 为 xlsx，设置 Content-Disposition 为 attachment

## 4. ViewSet：Excel 批量导入端点

- [x] 4.1 在 CategoryViewSet 中新增 `@action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import')` 方法
- [x] 4.2 实现文件解析逻辑：读取上传的 Excel 文件，从第 2 行开始逐行读取，映射列到 Category 字段
- [x] 4.3 逐行创建 Category 记录，捕获异常收集错误信息，返回 `{imported, errors}` 响应
- [x] 4.4 处理边界情况：未上传文件返回 400，文件格式错误返回 400

## 5. 验证

- [x] 5.1 启动开发服务器，测试 `GET /api/categories/template/` 返回 xlsx 文件
- [x] 5.2 测试 `POST /api/categories/import/` 上传 Excel 文件成功导入
- [x] 5.3 测试 `POST /api/categories/` 创建分类时传入 `attribute_template` 数据
- [x] 5.4 测试 `GET /api/categories/:id/` 响应中包含 `属性模板` 字段
- [x] 5.5 确认前端分类页面属性模板保存和 Excel 导入功能正常工作
