## Context

当前侧边栏"采购入库"指向 `/assets/purchase` → `Purchase.vue`，该页面没有导出按钮。
其他 5 个流转页面（AssignList、ReturnList、TransferList、RepairList、ScrapList）通过 `useTransferList` composable 共享导出逻辑，但当前导出仅导出当前页已加载的数据（前端 XLSX 生成），不传筛选参数给后端。

后端 `exportTransfers` API 已支持 params 参数（`/api/transfers/export`），可按 type、status、fromBranch、toBranch 筛选。

## Decisions

1. **修改 composable 导出逻辑** — `useTransferList.ts` 的 `handleExport` 改为调用后端 `exportTransfers` API，将当前 filters（fromBranch、toBranch、status）和 type 一起传给后端，由后端生成完整 Excel 并返回 blob
2. **Purchase.vue 增加导出按钮** — 在页面 header-actions 中添加导出按钮，直接调用 `exportTransfers({ type: 'purchase' })` 下载 Excel
3. **导出文件名区分类型** — 每种流转类型的导出文件名包含类型名称（如 `采购入库_2026-04-10.xlsx`）

## Risks / Trade-offs

- [前端 XLSX 生成的备选方案保留] — 如果后端 API 调用失败，不回退到前端 CSV 导出（与批量导入模板下载保持一致，都走后端）
