## Why

库存模块的「资产列表」与「固定资产表」目前只支持**逐条删除**（两者单删均已存在），缺少**批量删除**能力。当需要清理大量过期、错误或报废记录时，逐条删除效率低、易漏。应支持勾选多行后一次性删除。

## What Changes

- **资产列表（AssetList.vue）**：复用既有行多选与批量操作栏（已有「批量打印 / 批量调拨」），新增「批量删除」按钮——勾选 → 二次确认（显示数量）→ 调批量删除接口 → 刷新。
- **固定资产表（FixedAssetList.vue）**：新增行多选（复选框 + 全选 + `selectedFixedAssets`）与批量操作栏，含「批量删除」按钮与同样流程。
- **后端**：`AssetViewSet` 与 `FixedAssetViewSet` 各新增 `batch_delete` action（`POST`，接收 `ids` 列表），**按数据范围（DataScopeMixin）过滤后批量删除**，权限与单删一致（`manage_assets`）。
- **前端 api**：新增 `batchDeleteAssets(ids)` / `batchDeleteFixedAssets(ids)`。
- **权限**：批量删除同样要求 `manage_assets`（与单删一致），无权限者看不到批量删除入口。

## Capabilities

### New Capabilities
- `asset-batch-delete`: 在资产列表与固定资产表中批量勾选并一次性删除多条记录，含后端批量删除接口（数据范围隔离 + 权限）与前端批量入口。

### Modified Capabilities
<!-- 无：现有 specs 中不含资产/固定资产批量删除 capability。 -->

## Impact

- **后端** `apps/assets/views.py`：`AssetViewSet`、`FixedAssetViewSet` 各加 `batch_delete` action 与 `required_operations` 映射。
- **前端** `AssetList.vue`（批量栏加「批量删除」）、`FixedAssetList.vue`（加多选 + 批量栏 + 批量删除）、`api/assets.ts`（两个批量删除 helper）。
- **测试**：后端 `batch_delete`（命中计数、数据范围隔离越权 id、无权限 403）；前端 vue-tsc 通过。
- 无 DB 迁移。
