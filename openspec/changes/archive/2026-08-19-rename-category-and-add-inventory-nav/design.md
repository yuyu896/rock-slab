## Context

当前侧边栏导航在 `SidebarNav.vue` 的 `navItems` 计算属性中硬编码。菜单为扁平结构加一个可展开的「资产流转」分组。需要将「资产分类」更名为「品目」，并新增「库存」分组包含资产列表和固定资产表。

## Goals / Non-Goals

**Goals:**
- 侧边栏「资产分类」→「品目」，Category.vue 页面标题同步修改
- 新增「库存」分组（与「资产流转」同级的可展开菜单）
- 「资产列表」移入「库存」分组下
- 新增「固定资产表」页面入口，路由 `/fixed-assets`
- 固定资产表复用 getAssets API，默认筛选 `category=固定`

**Non-Goals:**
- 不修改后端 API
- 不修改移动端导航（仅 PC 端侧边栏）
- 不修改 Category.vue 的功能逻辑，仅改标题文案

## Decisions

### 1. 侧边栏分组结构

在 `SidebarNav.vue` 的 `navItems` 中，将「资产列表」从顶层改为 `children` 模式（与「资产流转」相同的展开/折叠模式），父级为「库存」。新增「固定资产表」作为第二个子项。

### 2. 固定资产表页面

新增 `FixedAssetList.vue`，基于 `AssetList.vue` 简化：移除分类筛选（固定为「固定」），保留分公司/状态/关键词筛选和分页。复用 `getAssets` API 并传 `category=固定` 参数。

### 3. 路由配置

在 `router/index.ts` 中新增 `/fixed-assets` 路由，指向 `FixedAssetList.vue`。资产列表的路由 path `/assets/list` 不变（仅侧边栏层级调整）。

## Risks / Trade-offs

- **导航变动的用户习惯** → 变更较小，仅重组和新增，不影响功能
- **固定资产表与资产列表代码重复** → 初期可接受，后续可抽取公共组件
