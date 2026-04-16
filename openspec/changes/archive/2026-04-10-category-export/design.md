## Context

资产分类模块已有完整的 Excel 模板下载和批量导入功能（通过 openpyxl），后端 CategoryViewSet 中已实现 `download_template` 和 `import_excel` 两个 action。前端 Category.vue 页面头部有"导入"和"新增分类"按钮，但缺少"导出"按钮。

后端 AssetViewSet 中已有 `export_excel` action 可作为参考模式。

## Goals / Non-Goals

**Goals:**
- 后端新增 `GET /api/categories/export/` 端点，使用 openpyxl 导出分类数据为 xlsx
- 导出支持筛选参数（资产类目、关键词），仅导出筛选后的数据
- 前端 Category.vue 新增"导出"按钮，点击即下载

**Non-Goals:**
- 不支持自定义导出列（固定导出所有主要字段）
- 不支持导出为 CSV 或其他格式
- 不修改后端模型或权限逻辑

## Decisions

### 1. 复用 AssetViewSet.export_excel 模式

**选择**：使用 `@action(detail=False, methods=['get'], url_path='export')` + openpyxl Workbook + HttpResponse 返回文件
**理由**：与项目现有导出模式一致，代码风格统一，前端可直接通过 GET 请求触发下载

### 2. 前端导出方式：直接 window.open

**选择**：前端通过 `window.open(url)` 或创建隐藏 `<a>` 标签触发下载，而非 axios 请求
**理由**：GET 请求 + 文件下载，浏览器原生处理最简单可靠，无需处理 blob 转换。筛选参数通过 URL query string 传递。

**备选**：axios + blob → 增加前端代码复杂度，无额外收益。

### 3. 导出字段

固定导出列：资产类目、物品分类、资产名称、资产编号、计量单位、资产数量、在库数量、警戒线、备注

## Risks / Trade-offs

- **大数据量导出性能**：分类数据量通常不大（几十到几百条），无需流式导出 → 直接内存生成即可
