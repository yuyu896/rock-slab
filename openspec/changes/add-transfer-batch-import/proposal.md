## Why

资产流转页面目前只支持逐条新建流转单（领用/归还/调拨/维修/报废），对于初始化或批量操作场景效率极低。后端 Transfer 模型已支持 6 种 action_type，但缺少批量导入 API 和前端入口。需要同时补齐后端导入/导出接口和前端批量导入交互。

## What Changes

- 后端 `TransferViewSet` 新增 `import_excel` action（POST `/api/transfers/import`），支持 Excel 批量导入流转记录
- 后端 `TransferViewSet` 新增 `export_excel` action（GET `/api/transfers/export`），支持导出流转记录和下载导入模板
- 前端 `transfers.ts` 新增 `importTransfers()` 和 `exportTransfers()` API 方法
- 前端 `Transfer.vue` 操作栏新增"批量导入"按钮，复用与资产列表一致的弹窗交互（下载模板 → 上传文件 → 查看结果）

## Capabilities

### New Capabilities
- `transfer-batch-import`: 前端流转页面批量导入功能，包括后端导入/导出 API、前端 API 方法、批量导入按钮和弹窗交互

### Modified Capabilities

（无，不涉及已有 spec 行为变更）

## Impact

- **后端**：`backend/apps/transfers/views.py` 新增 import_excel / export_excel action；`backend/apps/transfers/serializers.py` 无需改动
- **前端 API**：`frontend/src/api/transfers.ts` 新增两个方法
- **前端页面**：`frontend/src/views/Transfer.vue` 新增批量导入按钮和弹窗
