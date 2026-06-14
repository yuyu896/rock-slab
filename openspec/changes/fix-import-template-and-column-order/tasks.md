## 1. 后端 — 新增模板下载 API

- [x] 1.1 在 `transfers/views.py` 中新增 `download_template` action，返回含 14 列表头的空 xlsx 文件
- [x] 1.2 在 `assets/views.py` 中新增 `download_template` action，返回含 23 列表头的空 xlsx 文件（按新列顺序）

## 2. 后端 — 调整资产列顺序

- [x] 2.1 修改 `assets/views.py` 的 `export_excel`，按新 23 列顺序输出（分公司编号与资产编号互换、电脑序列号提前、新增图片列）
- [x] 2.2 修改 `assets/views.py` 的 `import_excel`，按新 23 列顺序解析（跳过图片列）

## 3. 前端 — API 层

- [x] 3.1 在 `api/assets.ts` 中新增 `downloadAssetTemplate()` 函数，调用 `GET /api/assets/template`
- [x] 3.2 在 `api/transfers.ts` 中新增 `downloadTransferTemplate()` 函数，调用 `GET /api/transfers/template`

## 4. 前端 — 模板下载逻辑修复

- [x] 4.1 修改 `AssetImportDialog.vue`，模板下载改为调用 `downloadAssetTemplate()`
- [x] 4.2 修改 `PurchaseImportDialog.vue`，模板下载改为调用 `downloadAssetTemplate()`（移除静态文件下载逻辑）- [x] 4.3 修改 `useTransferList.ts` 的 `downloadTemplate`，改为调用 `downloadTransferTemplate()`

## 5. 前端 — 统一弹窗样式

- [x] 5.1 统一 `AssetImportDialog.vue` 弹窗样式：标题"批量导入资产"、下载模板按钮、上传区域、导入结果展示
- [x] 5.2 统一 `CategoryImportDialog.vue` 弹窗样式，与 AssetImportDialog 保持一致
- [x] 5.3 统一 `PurchaseImportDialog.vue` 弹窗样式，与 AssetImportDialog 保持一致
- [x] 5.4 统一流转页面（PurchaseList/TransferList/AssignList）内联导入弹窗样式，与其他弹窗保持一致
