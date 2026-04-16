## Why

资产管理模块目前只支持单条新增资产，对于初始化大量资产或批量更新场景效率极低。产品说明书已规划"资产导入"功能（Phase 4），后端 API `/api/assets/import` 已实现，但前端缺少对应的批量导入入口和交互流程。需要补齐前端批量导入能力，让用户能够通过 Excel 模板快速导入资产数据。

## What Changes

- 在资产列表页面（AssetList.vue）的操作栏中新增"批量导入"按钮
- 新增批量导入弹窗，支持以下交互流程：
  - 下载导入模板（Excel 格式）
  - 上传填写好的 Excel 文件
  - 展示导入结果（成功数量、失败数量、错误明细）
- 导入模板字段与资产信息字段一致（序号、分公司、资产编号、资产类目、物品分类等）

## Capabilities

### New Capabilities
- `asset-batch-import`: 前端资产列表批量导入功能，包括导入按钮、上传弹窗、模板下载、结果展示

### Modified Capabilities

（无，后端 API 已就绪，仅需前端对接）

## Impact

- **前端代码**：`frontend/src/views/AssetList.vue` 新增批量导入按钮和弹窗交互
- **前端 API**：`frontend/src/api/assets.ts` 已有 `importAssets()` 方法，无需新增
- **后端**：`/api/assets/import` 和 `/api/assets/export` 已实现，无需改动
- **依赖**：使用已有的 `importAssets()` API 和 Element Plus 组件
