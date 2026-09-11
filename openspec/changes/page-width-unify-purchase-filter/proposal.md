# 列表页版宽统一 1600 + 采购列表补分公司筛选

## Why

各列表页版宽不一：采购/领用/调拨/盘点为 1400px 居中，回收单 1600px，回收台账 100% 占满——宽屏下观感割裂。用户以回收单（1600px）为合适基准，要求统一。另：采购入库列表缺分公司筛选（领用已有调出/调入筛选），大范围账号查找困难。

## What Changes

- 版宽统一 **1600px**（`max-width: 1600px; margin: 0 auto`）：采购入库、领用出库、调拨、资产盘点四页 1400→1600；回收台账 100%→1600；回收单维持 1600
- 采购入库列表筛选区补**分公司筛选**（口径=入库分公司/调入方）：复用 BranchFilterSelect 可搜索组件，筛选参数 `toBranch`（后端 filterset 现成），空=全部
- 非目标：领用出库筛选不动（调出/调入已有）；其他页面版宽不动（实例档案/台账等另行口径，用户未提出）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `list-page-flex-layout`: 新增版宽统一要求（核心业务列表页 1600px 基准）
- `purchase-warehousing`: 采购入库列表补分公司筛选（入库分公司口径）

## Impact

- **前端**: PurchaseList/AssignList/TransferList/Inventory/RecoveryLedger 五页容器样式一行改动；PurchaseList 加筛选控件与 toBranch 参数透传
- 后端零改动（filterset 已支持 toBranch）
