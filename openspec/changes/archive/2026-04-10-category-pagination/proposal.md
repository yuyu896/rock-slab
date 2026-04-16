## Why

资产分类模块当前后端 `pagination_class = None`，前端一次性加载所有分类数据。随着分类数据增长，一次性加载会导致页面渲染变慢、内存占用增加。需要改为分页展示，提升加载性能和用户体验。

## What Changes

- 后端 CategoryViewSet 移除 `pagination_class = None`，继承项目默认的 `StandardPagination`（每页 20 条，支持 `page` 和 `pageSize` 参数）
- 前端 `api/categories.ts` 的 `getCategories` 函数适配分页响应格式（`{count, results}`）
- 前端 `Category.vue` 新增分页状态管理（当前页、每页条数、总数）和分页组件
- 筛选条件变更时重置到第 1 页
- 统计卡片改为从后端独立获取或基于全量数据（保持准确）

## Capabilities

### New Capabilities
- `category-pagination`: 资产分类分页展示功能，含后端分页 API 和前端分页组件

### Modified Capabilities

## Impact

- **后端**: `backend/apps/categories/views.py` 移除 `pagination_class = None`，API 响应格式从数组变为 `{count, results}`
- **前端 API**: `frontend/src/api/categories.ts` 适配分页参数和响应
- **前端视图**: `frontend/src/views/Category.vue` 新增分页状态和 UI 组件
- **兼容性**: 分页参数可选，默认行为自动分页
