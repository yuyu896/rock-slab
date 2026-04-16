## Why

当前资产流转模块的导出功能存在两个问题：

1. **采购入库页面（Purchase.vue）缺少导出功能** — 侧边栏"采购入库"指向的 Purchase.vue 没有数据导出按钮，用户无法导出采购入库记录
2. **所有流转页面的导出未传递筛选条件** — 当前 useTransferList composable 中的 handleExport 只导出当前页面已加载的数据（最多 20 条），不支持按分公司、状态等筛选条件导出全量数据，且导出时未调用后端 API 获取完整数据集

## What Changes

- 在 Purchase.vue 中增加导出按钮，复用 useTransferList 的导出逻辑或调用后端导出 API
- 修改 useTransferList composable 的 handleExport 方法，将当前筛选条件（fromBranch、toBranch、status）传递给后端 `exportTransfers` API，由后端生成带筛选的完整 Excel
- 确保所有 6 个流转类型页面的导出均支持按分公司、状态筛选导出

## Capabilities

### New Capabilities
- `transfer-export-filter`: 流转记录导出支持按分公司和状态筛选，采购入库页面新增导出功能

### Modified Capabilities

（无已有 spec 行为变更）

## Impact

- **前端 composable**: `useTransferList.ts` 的 handleExport 改为调用后端 API 并传递筛选参数
- **前端页面**: `Purchase.vue` 新增导出按钮和逻辑
- **前端 API**: `exportTransfers` 已支持 params 参数，无需修改
- **后端**: 无变更（export API 已支持查询参数筛选）