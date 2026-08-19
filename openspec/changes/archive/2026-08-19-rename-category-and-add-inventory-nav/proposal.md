## Why

业务术语调整：「资产分类」改为「品目」更贴合实际使用习惯。导航结构需要优化：资产相关页面应归入「库存」分组下统一管理，同时新增独立的「固定资产表」页面供固定资产专项管理。

## What Changes

- 侧边栏「资产分类」改名为「品目」，页面标题同步修改
- 侧边栏新增「库存」一级分组（可展开/折叠），包含「资产列表」和新增的「固定资产表」
- 「资产列表」从顶层菜单移入「库存」分组下
- 新增固定资产表页面（`/fixed-assets`），筛选 `资产类目=固定`，复用资产 API

## Capabilities

### New Capabilities
- `inventory-nav-group`: 库存导航分组及固定资产表页面

### Modified Capabilities
（无已有 spec 需要修改）

## Impact

- **前端**: `SidebarNav.vue`（菜单结构）、`router/index.ts`（新增路由）、`Category.vue`（标题改名）、新增 `FixedAssetList.vue` 页面
- **后端**: 无变更，固定资产表复用现有 assets API
