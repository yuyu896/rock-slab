## Why

侧边栏"资产盘点"菜单项的数字角标硬编码为 `3`，不会反映实际的待处理盘点任务数量。用户无法通过角标了解当前有多少待盘点任务，降低了导航的实用性和信息价值。

## What Changes

- 移除 SidebarNav.vue 中 `badge: 3` 的硬编码值
- 在 SidebarNav 组件中动态获取 `pending` + `in_progress` 状态的盘点任务数量
- 将角标数字绑定到响应式数据，仅在数量 > 0 时显示
- 复用已有的 `getInventoryTasks` API，与移动端 Home.vue 保持一致的获取方式

## Capabilities

### New Capabilities
- `dynamic-inventory-badge`: 侧边栏盘点角标动态数据获取与显示，仅在有待处理任务时展示角标

### Modified Capabilities

## Impact

- 前端文件: `frontend/src/components/layout/SidebarNav.vue`
- 可能涉及: `frontend/src/api/inventories.ts`（已有，无需修改）
- API 依赖: `GET /api/inventories/?status=pending,in_progress&pageSize=1`
- 性能: 侧边栏挂载时增加一次轻量 API 请求（仅获取 count）
