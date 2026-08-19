# 修复前端 API URL 尾部斜杠不匹配及采购入库流程

## 问题

### 1. API URL 尾部斜杠不匹配
- 后端 `DefaultRouter(trailing_slash=False)` + `APPEND_SLASH=False` + 主 `urls.py` 用 `path('api/xxx/', ...)`
- **列表/创建 URL**（`/api/xxx/`）：需要尾部斜杠（匹配 `path()` 前缀）
- **detail/action URL**（`/api/xxx/{id}`, `/api/xxx/purchase`）：不需要尾部斜杠（router 生成）
- 前端部分 action URL（如 `purchase/`, `assign/`）带尾部斜杠导致 404

### 2. 采购入库使用错误 API
- `submitOrder` 和 `saveDraft` 调用 `createAsset()` (POST /api/assets/)，但 AssetViewSet 是只读的
- 应使用 `purchaseAsset()` (POST /api/transfers/purchase)

### 3. 采购入库传参错误
- 前端传 `调入分公司: order.branch`（分公司 ID/UUID）
- 后端 `TransferActionSerializer` 的 `调入分公司` 是 CharField，期望分公司名称
- 应使用 `to_branch` FK 字段传递 ID

### 4. CSS 变量 `--color-primary` 未定义
- `variables.css` 只定义了 `--color-primary-50` ~ `--color-primary-900`
- `InventoryTaskList.vue` 等组件使用 `var(--color-primary)` 导致按钮不可见

### 5. 盘点筛选栏缺少分公司下拉
- `InventoryTaskList.vue` 收到 `branchOptions` prop 但未渲染分公司筛选器

## 影响范围

- `frontend/src/api/` — 所有 API 文件的 URL 尾部斜杠修正
- `frontend/src/views/Purchase.vue` — 改用 purchaseAsset API + to_branch FK
- `frontend/src/styles/variables.css` — 添加 --color-primary
- `frontend/src/views/inventory/InventoryTaskList.vue` — 添加分公司筛选
