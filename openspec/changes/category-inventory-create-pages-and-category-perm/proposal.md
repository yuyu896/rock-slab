## Why

延续 `dialogs-to-pages-and-profile-fixes` 的模式（资产 / 固定资产 / 流转的新增已从弹窗改为独立路由页面），仍有两处"新增"以内嵌弹窗实现，窄屏填写局促、遮挡列表上下文：

1. **品目模块（Category）**：新增 / 编辑品目用 `CategoryForm` 模态弹窗。
2. **资产盘点**：创建盘点任务用 `showCreateTaskModal` 弹窗（`modal-overlay`）。

此外，品目模块的写权限（新增 / 编辑 / 删除 / 导入）后端已由 `manage_categories` 操作码 gating（解耦变更落地），但**前端未按此控制**——所有登录用户都能看到并触发写操作入口，仅在后端被拒时才失败，体验差且暴露无意义入口。需让没有 `manage_categories` 权限的用户在品目页**纯只读**（隐藏写操作入口）。

## What Changes

- **品目新增 / 编辑改为独立路由页面**：新增 `views/categories/CategoryCreate.vue`（承载新增；编辑复用或单独页面），列表页"新增"按钮改为 `router.push('/categories/create')`；移除 `CategoryForm` 模态用法。
- **创建盘点任务改为独立路由页面**：新增 `views/inventory/InventoryTaskCreate.vue`，盘点列表页"创建任务"改为 `router.push('/inventory/create')`；移除 `showCreateTaskModal` 弹窗。
- **品目写权限按 `manage_categories` 控制（前端）**：品目列表页的新增 / 编辑 / 删除 / 导入按钮，仅当 `can('manage_categories')` 为真时显示；无权限用户只见列表（只读）。后端 `manage_categories` gating 已就绪，无需改动。

## Capabilities

### New Capabilities
<!-- 无新增能力 -->

### Modified Capabilities
- `management-permissions`: 品目写操作（新增 / 编辑 / 删除 / 导入）的前端入口 MUST 按 `manage_categories` 操作授权控制可见性；无该授权的非 admin 用户 MUST 仅可见只读品目列表。

## Impact

- **前端（新增页面）**：`views/categories/CategoryCreate.vue`、`views/inventory/InventoryTaskCreate.vue`；`router/index.ts` 增加 `/categories/create`、`/inventory/create` 路由。
- **前端（改造）**：`views/Category.vue`（移除 `CategoryForm` 模态、"新增"改跳转、写按钮按 `can('manage_categories')` 显示）、`views/Inventory.vue`（移除 `showCreateTaskModal`、"创建任务"改跳转）。
- **前端权限**：`hooks/usePermission` 已有 `canManageCategories`（`can('manage_categories')`），直接复用。
- **后端**：无接口契约变更；`manage_categories` gating 已就绪。
- **不在本次范围**：品目的批量导入弹窗（`CategoryImportDialog`）是否一并改为页面（本次仅按权限控制其入口可见性，不改为页面）；盘点任务的编辑（若存在）。
- **回归验收**：新增品目 / 创建盘点任务表单提交与取消；无 `manage_categories` 的用户在品目页看不到写入口、调写接口被 403；有权限用户正常。
