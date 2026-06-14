## Why

批量导入模板存在两处重复：采购入库页（Purchase.vue）的导入弹窗和资产列表页（AssetList.vue）下载的是同一个"资产导入模板.xlsx"；领用出库（AssignList.vue）和调拨（TransferList.vue）页面的导入模板内容也完全一样。用户在不同业务场景下看到一模一样的模板，容易混淆且不符合业务语义。

## What Changes

- 采购入库页的导入弹窗（PurchaseImportDialog.vue）应使用采购专属模板，而非通用的资产导入模板
- 领用出库和调拨页面的导入模板应使用各自业务类型的专属表头/文件名，而非共享同一个 14 列流转记录模板
- 在 `importTemplate.ts` 中新增采购入库专属模板生成函数和领用/调拨各自的模板定义

## Capabilities

### New Capabilities

_无新增能力_

### Modified Capabilities

- `import-templates`: 各业务页面的导入模板应按业务类型区分，采购入库用采购专属模板，领用出库和调拨用各自业务模板

## Impact

- `frontend/src/utils/importTemplate.ts` — 新增采购入库、领用出库、调拨各自的模板定义
- `frontend/src/views/purchases/PurchaseImportDialog.vue` — 改用采购入库专属模板
- `frontend/src/composables/useTransferList.ts` — 领用和调拨分别调用不同的模板生成函数
