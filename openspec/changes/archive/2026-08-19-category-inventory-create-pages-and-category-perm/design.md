## Context

延续 `dialogs-to-pages-and-profile-fixes`：资产 / 固定资产 / 流转（采购/领用/调拨/回收）的新增已抽为独立 `*Create.vue` 路由页面，列表页"新建"按钮 `router.push` 跳转、提交后 `router.replace` 回列表。两处遗留弹窗：
- 品目：`views/Category.vue` 内嵌 `views/categories/CategoryForm.vue` 模态（`openCreate`/`editCategory`/`addCategory` 控制），含新增 + 编辑。
- 盘点：`views/Inventory.vue` 内 `showCreateTaskModal`（`modal-overlay`）创建盘点任务，提交调 `createInventoryTask`。

权限：解耦变更已让 `CategoryViewSet` 的 create/update/destroy/import_excel 走 `manage_categories` 操作码（`required_operations`）；前端 `usePermission` 已暴露 `canManageCategories = can('manage_categories')`。但 `Category.vue` 的写按钮未按此隐藏。

约束：Vue3 + vue-router；既有 create 页面可作模式参考（`AssetCreatePage.vue`、`transfers/PurchaseCreate.vue`）；品目表单字段与盘点任务字段需与原弹窗一致。

## Goals / Non-Goals

**Goals:**
- 品目新增 / 编辑、盘点创建任务，由弹窗改为独立路由页面，体验与既有 create 页面一致。
- 品目写操作入口按 `manage_categories` 授权控制可见性（无权限纯只读）。

**Non-Goals:**
- 不改品目 / 盘点的字段、校验、接口契约。
- 不把品目批量导入弹窗改为页面（仅按权限控制其入口可见性）。
- 不改后端权限逻辑（已就绪）。
- 不改盘点任务编辑（若存在）。

## Decisions

### 决策 1：品目新增与编辑复用同一 create 页面（带 id 参数区分模式）
新增 `views/categories/CategoryCreate.vue`，路由：
- `/categories/create` → 新增模式
- `/categories/:id/edit` → 编辑模式（读路由 id，拉取已有品目回填）
提交成功后 `router.replace('/categories')` 并触发列表刷新（通过路由返回或 store/事件）。
**Why**：新增 / 编辑字段完全一致，复用一套表单组件减少重复，与"一个表单页两种模式"的常见做法一致。
**Alternatives**：新增 / 编辑各一个页面 → 字段重复维护（否决）；保留编辑弹窗只改新增 → 不一致（否决）。

### 决策 2：盘点创建任务独立页面 `views/inventory/InventoryTaskCreate.vue`
路由 `/inventory/create`，字段与原 `showCreateTaskModal` 一致（名称、分公司、分类等），提交调 `createInventoryTask`，成功后 `router.replace('/inventory')` 并选中 / 刷新新建任务。
**Why**：与品目 / 资产 create 页面模式统一。

### 决策 3：品目写入口按 `canManageCategories` 显示
`Category.vue` 顶部"新增分类"按钮、行内"编辑 / 删除"按钮、导入入口，统一加 `v-if="canManageCategories"`。`canManageCategories` 来自 `usePermission()`（已实现 `can('manage_categories')`，admin 恒真）。
**Why**：后端已 gating，前端补齐可见性，避免无权限用户看到无意义入口后被 403。

### 决策 4：列表刷新机制
create 页面提交后返回列表，列表通过 `onActivated`（若用 keep-alive）或返回时重新拉取来刷新。沿用既有 create 页面的返回刷新约定（`router.replace` 回列表 + 列表 `onMounted`/路由触发刷新）。
**Why**：与既有 create 页面行为一致，不引入新状态管理。

## Risks / Trade-offs

- **[编辑模式回填字段遗漏]** → create 页面编辑模式必须覆盖原 `CategoryForm` 全部字段；以原弹窗字段清单为基线逐项核对。
- **[列表返回不刷新]** → 沿用既有 create 页面的 `router.replace` + 列表刷新约定；若发现不刷新，补 `onActivated` 或 query 触发。
- **[无权限用户仍能通过 URL 直访 create 页面]** → create 页面本身不强制权限（后端 create 接口已 403 拦截）；可在路由 meta 加 `requiresOperation` 守卫作为增强（本次可选）。
- **[盘点创建任务字段较多]** → 直接迁移原弹窗字段，不改逻辑。
