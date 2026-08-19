## Why

资产列表批量导入模板由**前端** `utils/importTemplate.ts` 的 `generateAssetTemplate()` 客户端生成，其 `ASSET_HEADERS` 仍是旧的 23 列（序号、电脑序列号、图片、警戒线、是否充足、使用人…），导致用户下载到的模板仍含多余列。之前误改了后端 `/api/assets/template`（前端并未调用它），未生效。

## What Changes

- 把 `frontend/src/utils/importTemplate.ts` 的 `ASSET_HEADERS` 改为指定 **15 列**：分公司、资产编号、资产类目、物品分类、资产名称、入库日期、是否租用、数量、规格、单价、购入金额、出库日期、所属部门、当前状态、备注。
- 固定资产模板走后端（已正确），不动。

## Capabilities

### New Capabilities
- `asset-import-template-columns`: 前端资产导入模板（`importTemplate.ts`）的列集合——恰好为指定的 15 列。

### Modified Capabilities
<!-- 纠正 import-templates-and-dedup（后端）未覆盖的前端模板生成路径。 -->

## Impact

- **前端** `utils/importTemplate.ts`（`ASSET_HEADERS`）。无后端、无 DB 迁移。
