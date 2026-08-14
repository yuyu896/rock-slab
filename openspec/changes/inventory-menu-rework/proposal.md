## Why

「库存」菜单下的「资产列表」实际展示的是每条资产的明细记录，名称与内容不符；缺少一个按分公司维度汇总资产编号的总览入口，用户要逐个分公司翻查明细才能掌握编号分布；侧边栏子菜单互斥展开（展开「资产流转」会自动收起「库存」），多组菜单项无法同时可见，操作效率低。

## What Changes

- **重命名**：「库存」菜单下的「资产列表」改名为「资产明细」，页面标题、导出文件名等页面内文案同步改为「资产明细」（路由路径 `/assets/list` 保持不变，不做 BREAKING 变更）。
- **新增「资产汇总」页**：「库存」子菜单最上方新增「资产汇总」入口（`/assets/summary`），表格按分公司汇总资产编号：分公司名称/编码、资产总数、资产编号起止范围（编号段）。此页先按模板交付，后续会专门调整汇总维度。
- **新增后端汇总接口**：`GET /api/assets/summary/` 按分公司聚合（总数、编号最小/最大值），走统一管理授权数据隔离（与报表 `_scope_queryset` 同源）。
- **修复侧边栏展开互斥**：`SidebarNav.vue` 的 `expandedMenu` 由单值改为集合，允许多个子菜单同时展开，点击已展开项仅收起自身。

## Capabilities

### New Capabilities

- `asset-summary`: 按分公司汇总资产编号的资产汇总页（前端表格 + 后端聚合接口），先提供模板化汇总维度。
- `sidebar-navigation`: PC 端主导航的菜单结构、命名（「资产明细」）与子菜单展开交互（允许多组同时展开）。

### Modified Capabilities

（无。）

## Impact

- **后端**：`apps/assets/views.py`（AssetViewSet 增加 `summary` 动作或独立视图）、`apps/assets/urls.py`；复用 `apps/permissions/scope.resolve_user_scope` 做数据隔离；`backend/tests/` 新增接口测试。
- **前端**：`components/layout/SidebarNav.vue`（菜单项、多展开）、`views/AssetList.vue`（文案）、新增 `views/assets/AssetSummary.vue`、`api/assets.ts`（`getAssetSummary`）、`router/index.ts`（`/assets/summary` 路由）、`types/`（汇总行类型）。
- **无数据库变更**，无迁移。
