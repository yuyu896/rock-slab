## Why

资产分类模块已支持 Excel 模板下载和批量导入，但缺少导出功能。用户需要将当前分类数据导出为 Excel 文件，用于数据备份、离线查看或跨系统传递。

## What Changes

- 后端 CategoryViewSet 新增 `GET /api/categories/export/` 端点，使用 openpyxl 导出分类数据为 xlsx 文件
- 导出支持当前筛选条件（资产类目、关键词），仅导出筛选后的数据
- 前端 Category.vue 页面头部新增"导出"按钮，调用导出端点下载文件
- 前端 `api/categories.ts` 新增 `exportCategories` API 函数

## Capabilities

### New Capabilities
- `category-export`: 资产分类 Excel 导出功能，含后端导出端点和前端导出按钮

### Modified Capabilities

## Impact

- **后端**: `backend/apps/categories/views.py` 新增 `export_excel` action
- **前端 API**: `frontend/src/api/categories.ts` 新增导出函数
- **前端视图**: `frontend/src/views/Category.vue` 页面头部新增导出按钮
- **依赖**: 无新依赖，openpyxl 已在项目中
