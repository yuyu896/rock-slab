## Why

列表页版宽已统一 1600（page-width-unify 变更），五种单据详情页仍卡 1080（TransferDetailLayout 共用样式）——从列表进详情视觉缩水 1/3，宽屏尤甚；明细表列多（品目/规格/供应商/数量/单价/金额/使用人/位置）在 1080 下拥挤。

## What Changes

- `TransferDetailLayout.vue` 的 `.detail-page` max-width **1080px → 1600px**（一行改动）
- 五种单据详情页（采购/领用/归还/调拨/回收）同步变宽

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `shared-ui-components`: 新增「单据详情页版宽 1600」需求（ADDED；TransferDetailLayout 为共享组件）

## Impact

- 前端：`views/transfers/components/TransferDetailLayout.vue` 一行 CSS
- 不动：`@media` 响应式断点（max-width 仅约束大屏）、移动端布局、其他页面版宽
- 防误伤边界：纯视觉样式，无逻辑参与；信息区为自适应 flex、明细表自适应列宽，加宽只会摊开不会换行错乱
