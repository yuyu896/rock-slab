## Why

新增资产、各类流转等表单要求用户既填「资产编号」、又手填「资产名称」（部分表单还要选「资产类目 / 物品分类」）。但「资产编号」本就唯一对应一条「资产分类 (Category)」记录——分类里已登记了名称、类目、分类。重复手填既低效，又容易出现编号与名称/分类不一致的脏数据。应做到：**填入编号即自动带出分类登记的名称（及类目/分类），未登记则提示**，让编号成为单一事实来源。

## What Changes

- 新增后端按编号**精确查询**分类的轻量接口 `GET /api/categories/lookup?asset_code=<code>`：命中返回 `{ asset_name, asset_category, item_category, unit }`，未命中返回 404。
- 前端新增 API helper（`lookupCategoryByCode`）与可复用组合式 `useAssetCodeAutofill`，统一封装「查询 + 带出 + 未登记提示」逻辑。
- 在所有含「资产编号 + 资产名称」手填字段的新增表单接入：资产编号**失焦**时触发查询；命中则带出名称（及该表单存在的资产类目/物品分类）；未命中则在编号输入处**内联提示**「该编号未在资产分类登记」。
- 覆盖表单：`AssetCreatePage`、`Assign/Purchase/Recovery/TransferCreate`、`PurchaseCreateForm`（多行表单逐行带出）。
- `FixedAssetCreate` 走既有「按编号查 Asset」逻辑（名称取自 Asset），机制不同，**不纳入**本变更。

## Capabilities

### New Capabilities
- `asset-code-autofill`: 在新增表单中按资产编号自动反查并带出资产分类登记的名称（及类目/分类），含编号未登记的内联提示行为，以及后端按编号精确查询分类的接口契约。

### Modified Capabilities
<!-- 无：现有 specs 中不含资产编号反查/自动带出相关 capability。 -->

## Impact

- **后端** `apps/categories/views.py`：`CategoryViewSet` 新增 `lookup` action（router 自动暴露路由）；无需迁移。
- **前端** `api/categories.ts`（lookup helper）、`composables/useAssetCodeAutofill.ts`（新增）、约 6 个新增表单 `.vue` 接入。
- **测试**：后端 lookup 接口（命中 / 未命中 / 缺参）；前端组合式行为（命中带出、未命中提示）。
