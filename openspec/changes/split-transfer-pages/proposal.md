## Why

当前资产流转页面（Transfer.vue）将 6 种流转类型（采购入库、领用出库、归还、调拨、维修、报废）混在一个页面内，通过 Tab 切换和共用一个弹窗。这导致：
- 页面代码臃肿（800+ 行），维护困难
- 新建表单逻辑混杂在一个弹窗中，通过 `createType` 条件渲染不同字段
- 侧边栏"调拨记录"无法直观看出还有领用、归还、维修、报废等子功能
- 用户需要先打开流转页面再切换 Tab，操作路径长

## What Changes

- 将侧边栏"资产管理"下的"调拨记录"改为"资产流转"分组，展开子菜单包含：采购入库、领用出库、归还、调拨、维修、报废
- 每种流转类型拆分为独立 Vue 页面组件，拥有独立的列表视图、筛选、新建弹窗
- 复用现有 API（`getTransfers` + 各 action 端点），不修改后端
- 原 Transfer.vue 改为路由重定向或删除

## Capabilities

### New Capabilities
- `split-transfer-pages`: 将混合流转页面拆分为 6 个独立页面，侧边栏子菜单导航

### Modified Capabilities

（无已有 spec 行为变更）

## Impact

- **前端路由**：`router/index.ts` 新增 6 个路由，移除原 `/assets/transfer`
- **前端侧边栏**：`MainLayout.vue` navItems 结构调整
- **新增页面**：6 个独立 Vue 组件（PurchaseList、AssignList、ReturnList、TransferList、RepairList、ScrapList）
- **原页面**：Transfer.vue 可删除或保留为"全部流转"聚合视图
- **后端**：无变更
