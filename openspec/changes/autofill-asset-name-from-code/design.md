## Context

- 「资产编号」(`Category.asset_code`) 在资产分类中唯一，每条分类同时登记了 `asset_name`、`asset_category`、`item_category`、`unit`。
- 多个新增表单（资产、领用/采购/退回/调拨）让用户**同时手填**资产编号与资产名称（部分还选资产类目/物品分类），编号与名称/分类易不一致。
- 后端 `CategoryViewSet` 为标准 DRF ViewSet；`CategoryFilterSet` 仅提供 `keyword`（icontains，含 asset_code）与 `资产类目/物品分类` 过滤，**无精确 asset_code 过滤**；list 接口分页。
- 前端表单字段为原生 `<input>`/`<select>` + `v-model`，资产类目/物品分类在 `AssetCreatePage` 等处为下拉。

## Goals / Non-Goals

**Goals:**
- 资产编号**失焦**时按编号精确反查分类，带出资产名称（及该表单存在的资产类目/物品分类）。
- 编号未登记时在编号输入处**内联提示**。
- 查询/带出逻辑跨多个新增表单**复用**。

**Non-Goals:**
- 不做输入实时联想/下拉搜索（仅失焦精确查询）。
- 不锁定带出字段——用户仍可修改。
- 不纳入 `FixedAssetCreate`（其按编号查 *Asset*、名称取自 Asset，机制不同——已确认）。

## Decisions

### 决策 1：后端用专用 `lookup` action，而非复用 list+filter
- **做法**：`CategoryViewSet` 新增 `@action(detail=False)` 的 `lookup`：`GET /api/categories/lookup?asset_code=<code>`，命中返回 `{ asset_name, asset_category, item_category, unit }`，未命中 404，缺参 400。
- **理由**：精确单条查询、响应轻量、语义清晰、前端无需处理分页。
- **备选**：给 `CategoryFilterSet` 加精确 `asset_code` 过滤，复用 list 接口——仍返回分页列表、需取 `results[0]`，偏重，**否**。

### 决策 2：前端用组合式 `useAssetCodeAutofill` 封装，跨表单复用
- **做法**：新增 `composables/useAssetCodeAutofill.ts`，暴露 `lookup(code)` 与 `loading / notFound` 状态；`api/categories.ts` 新增 `lookupCategoryByCode(code)`。
- **理由**：6 处表单避免重复实现查询/提示逻辑，行为统一、易维护。

### 决策 3：触发=失焦，带出=名称+类目+分类（仅填表单存在的字段），且不锁定
- **做法**：编号 `@blur` 触发查询；命中后用分类值回填表单中**存在**的名称/类目/分类字段；带出后字段仍可编辑。
- **理由**：失焦请求少、逻辑简洁（用户策略裁定）；不锁定保留纠错能力。

### 决策 4：未登记=内联提示，文案与后端校验一致
- **做法**：未命中时在编号输入处显示「该编号未在资产分类登记」红字提示；不清空用户已填内容。
- **理由**：与资产创建后端校验文案一致，提前告知，避免提交才报错。

### 决策 5：下拉型类目/分类字段的带出兼容
- **做法**：对 `AssetCreatePage` 等用 `<select>` 的类目/分类字段，带出时设置其 `v-model`；若选项来源不含该值则需保证选项与分类一致。
- **理由**：select 的 v-model 值须存在于选项中才会显示。实现时核对各表单选项来源，必要时调整（见 Open Questions）。

## Risks / Trade-offs

- **[select 带出值与选项不匹配]** 某表单类目/分类选项若不含分类登记的值，带出后下拉显示空 → **缓解**：实现时核对选项来源，必要时让选项取自分类或允许自由值。
- **[失焦查询网络延迟]** 查询期间用户可能已移到下一字段 → **缓解**：带 loading 态；失焦触发频率低，可接受。
- **[多行表单逐行查询]** `PurchaseCreateForm` 每行独立 blur → **缓解**：每行复用同一 helper，互不干扰。
- **[FixedAsset 机制不同]** 按 Asset 反查而非 Category → **缓解**：本变更不强行统一，单独评估（Open Questions）。

## Migration Plan

1. 后端：`CategoryViewSet` 加 `lookup` action，**无需数据库迁移**；router 自动暴露路由。
2. 前端：加 `lookupCategoryByCode` + `useAssetCodeAutofill`，逐表单接入。
3. 灰度：可先接 `AssetCreatePage` 验证带出/提示/下拉兼容，再推广其余表单。
4. 全量接入后跑 `vue-tsc`、前端测试、后端 `pytest`。

## Open Questions

1. 各表单类目/分类 `<select>` 的选项来源是否与分类登记值一致，带出是否需调整选项？（实现时核对。）

> 已定：`FixedAssetCreate` 不纳入本变更。
