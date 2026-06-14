## Why

测试发现三个影响用户使用的问题：1）采购入库的批量导入模板下载后为空白文件，用户无法按格式填写；2）资产列表的导入模板和数据表列顺序与业务需求不一致（缺少"图片"列，多列位置错乱）；3）各模块的批量导入实现方式不统一（有的用专用模板 API、有的下载全量数据当模板、有的下载静态文件），弹窗样式和交互也不一致。

## What Changes

- 修复采购入库流转页（PurchaseList）的模板下载逻辑，改为调用后端专用模板接口（新增 `GET /api/transfers/template`），返回带表头的空模板文件
- 为资产模块新增专用模板下载接口 `GET /api/assets/template`，返回与导入格式一致的空模板（含表头）
- 调整资产模块导入/导出的列顺序为：序号、分公司、资产编号、分公司编号、资产类目、电脑序列号、供应商、物品分类、资产名称、图片、入库日期、是否租用、数量、规格、单价、购入金额、出库日期、所属部门、使用人、当前状态、警戒线、是否充足、备注（共 23 列，新增"图片"列）
- 统一所有导入弹窗的模板下载方式：都调用专用模板 API
- 统一所有导入弹窗的样式和交互，使用共享组件 `ImportDialog.vue` 或统一各弹窗的模板结构

## Capabilities

### New Capabilities

- `unified-import-template`: 统一的批量导入模板下载机制，所有模块通过专用 API 获取带表头的空模板，而非下载全量数据

### Modified Capabilities

_(无现有 spec 需要变更)_

## Impact

- **后端**: `assets/views.py`（新增 template 端点 + 调整列顺序）、`transfers/views.py`（新增 template 端点）、`assets/urls.py`、`transfers/urls.py`
- **前端**: `AssetImportDialog.vue`、`CategoryImportDialog.vue`（样式对齐）、`PurchaseImportDialog.vue`、`PurchaseList.vue` / `TransferList.vue` / `AssignList.vue`（模板下载逻辑）、`useTransferList.ts`（模板下载）
- **API**: 新增 2 个 GET 端点（无 breaking change）
- **共享组件**: `ImportDialog.vue` 可能需要改造或被各专用弹窗参考统一样式
