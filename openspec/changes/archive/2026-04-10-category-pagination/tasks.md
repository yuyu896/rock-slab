## 1. 后端启用分页

- [x] 1.1 在 `backend/apps/categories/views.py` 中移除 `pagination_class = None`，改为显式设置 `pagination_class = StandardPagination`（从 `core.pagination` 导入）

## 2. 前端 API 适配

- [x] 2.1 修改 `frontend/src/api/categories.ts` 中 `getCategories` 函数，新增 `page` 和 `pageSize` 可选参数
- [x] 2.2 修改 Category.vue 中 `fetchCategories` 函数，传入分页参数，适配响应格式 `data.results` 和 `data.count`

## 3. 前端分页状态管理

- [x] 3.1 在 Category.vue 中新增 `pagination` ref（`{ page: 1, pageSize: 20, total: 0 }`）
- [x] 3.2 在 `fetchCategories` 中更新 `pagination.total = data.count`，将 `categories.value = data.results`
- [x] 3.3 新增 `handlePageChange(page)` 方法：更新 pagination.page 并重新 fetchCategories
- [x] 3.4 新增 `handlePageSizeChange` 方法：更新 pagination.pageSize、重置 page=1 并重新 fetchCategories
- [x] 3.5 在筛选条件变更时（watch filterCategory/filterKeyword）重置 pagination.page = 1

## 4. 前端分页 UI

- [x] 4.1 在表格视图和卡片视图下方添加分页组件 HTML（复用 AssetList.vue 的分页结构）
- [x] 4.2 添加分页组件 CSS 样式（pagination-section、pagination-controls、page-btn、size-select）

## 5. 验证

- [x] 5.1 测试后端 `GET /api/categories/?page=1&pageSize=20` 返回分页格式数据
- [x] 5.2 测试前端分页切换正常，页码高亮正确
- [x] 5.3 测试筛选条件变更后分页重置到第 1 页
- [x] 5.4 测试每页条数切换功能
