## Why

回收（RecoveryList）页面在浏览器视口缩小（如打开 F12 开发者工具面板）时不会自适应缩窄，导致内容溢出、无法正常使用。根本原因是 `.data-table` 设置了 `min-width: 1400px` 硬编码最小宽度，且页面容器链缺少有效的宽度约束（`overflow: hidden` / `min-width: 0`），表格无法被父级 flex/grid 容器限制宽度。

## What Changes

- 移除或降低 `.data-table` 的 `min-width: 1400px`，改为让表格在窄视口下通过 `.table-container` 的 `overflow-x: auto` 横向滚动
- 修复 `.transfer-page` 容器的宽度约束，确保 flex 子元素在视口缩小时能正确收缩
- 确保统计卡片（stats-row）、筛选栏（filter-row）在窄视口下正常响应式布局
- 检查其他流转页面（PurchaseList、AssignList、TransferList）是否存在同样问题，统一修复

## Capabilities

### New Capabilities

- `transfer-page-responsive`: 流转类页面（采购、领用、调拨、回收）的响应式布局修复，确保在窄视口下表格横向滚动、统计卡片和筛选栏自适应

### Modified Capabilities

## Impact

- `frontend/src/views/transfers/RecoveryList.vue` — CSS 样式调整
- `frontend/src/views/transfers/` 下其他流转页面 — 统一修复相同问题
- `frontend/src/layouts/MainLayout.vue` — 检查 `.main` / `.content` 容器是否需要 `overflow` 或 `min-width` 修复
- 纯 CSS 变更，无 API / 后端影响
