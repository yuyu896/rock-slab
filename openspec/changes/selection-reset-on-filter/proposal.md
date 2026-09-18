# 筛选变化清空实例勾选

## Why

实例档案勾选集（selectedIds）跨筛选持久：勾选手机后筛选电脑，手机勾选仍残留——「批量操作（N）」计数虚高含隐形勾选、序列号批量弹窗行数与 N 错位（按当前页命中建行）、用户误以为会改到看不见的实例。勾选语义应绑定当前数据集。

## What Changes

- 实例档案筛选条件变化（关键字/分公司/状态/仅待补录）时**清空勾选集**——换数据集即重置选择
- 翻页**保留**勾选（同一数据集内跨页勾选，切回可见，用于跨页批量打印）
- 非目标：批量操作端点逻辑不动；其他列表无勾选无涉

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fixed-asset-instance`: 勾选生命周期——随筛选重置

## Impact

- **前端**: 仅 `FixedAssetList.vue`（filters watch 清 selectedIds）；vitest
