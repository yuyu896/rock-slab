## 1. 改造模板生成函数

- [x] 1.1 修改 `importTemplate.ts` 中的 `generateTransferTemplate()`，接收 `type` 和 `label` 参数，在生成的 Excel 中预填"流转类型"列为 label 值，文件名使用 type 参数

## 2. 修改采购入库页导入弹窗

- [x] 2.1 修改 `PurchaseImportDialog.vue`：将 `generateAssetTemplate()` 替换为 `generateTransferTemplate('采购入库导入模板', '采购入库')`，将 `importAssets()` 替换为 `importTransfers()`，更新弹窗标题为"批量导入采购记录"

## 3. 修改领用/调拨模板调用

- [x] 3.1 修改 `useTransferList.ts` 中的 `handleDownloadTemplate()`，根据 type 分别传入对应参数：purchase→'采购入库'、assign→'领用出库'、transfer→'调拨'
