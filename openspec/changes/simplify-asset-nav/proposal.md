## Why

侧边栏"资产管理"分组下目前只剩"资产列表"一个子项（"采购入库"和"调拨记录"已在之前的拆分中移到"资产流转"分组）。只有一个子项的折叠菜单增加了不必要的操作步骤（需要先展开再点击），应该直接作为平级导航项展示。

## What Changes

- 将侧边栏"资产管理"从折叠分组改为平级导航项，直接链接到 `/assets/list`
- 移除 children 数组，使用与其他平级项（工作台、统计报表等）相同的展示方式

## Capabilities

### New Capabilities
- `simplify-asset-nav`: 将"资产管理"从折叠分组简化为直接导航链接

### Modified Capabilities

（无已有 spec 行为变更）

## Impact

- **前端侧边栏**: `MainLayout.vue` navItems 中"资产管理"项从带 children 的分组改为无 children 的平级项
- **路由**: 无变更，`/assets/list` 路由保持不变
