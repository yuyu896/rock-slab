## Why

写单页的选项没有收口：分公司下拉对所有人显示**全部**分公司（`BranchViewSet` 无范围过滤），员工采购入库可选到别家分公司、提交才被 400 拒；品目点选器（`ItemPicker`）查的是全量字典，不看所选分公司有没有货，领用/调拨/回收常选到数量为 0 的品目、提交才被台账充足性校验拦截。两处防线都在提交端，体验差（议题 14，2026-08-28 定案）。

## What Changes

- **分公司接口加范围参数**：`GET /api/branches?scope=write` 服务端按 `resolve_user_scope` 过滤，仅返回授权范围内分公司；**无参维持全量**（兼容既有筛选/管理页等 8 处调用）。
- **写单页分公司下拉收口**：采购·入库分公司、领用·所属分公司、调拨·**调出**分公司、回收·调出分公司 → 仅列授权范围内分公司；**调拨·调入分公司维持全量**（修订 3.1 单边化设计，调入方任意）。PC 四个创建页 + 移动端三个开单页同口径。
- **品目点选器按"扣数列"过滤**（PC 写单页 `ItemPicker`）：领用（新品库）→ 该分公司在库>0；领用（回收库）→ 回收库>0（消耗品剔除）；调拨 → 在库>0；回收 → 在用>0；采购 → 不过滤（生成制，扣数列为无）。选项行同时显示对应列的可用数量。未选分公司时品目入口禁用并引导先选分公司。
- **数据来源**：品目过滤复用台账接口 `/api/assets/summary`（已具备品目字段联查、keyword 检索、授权范围过滤），新增"指定列>0"筛选参数；不扩权限接口（2026-08-28 与用户议定）。
- 提交端校验（`validate_branches_in_scope` + 台账充足性）**全部保留不动**——本次是纯选项收口（防线前移），不是权限模型变更。

## Capabilities

### New Capabilities

- `branch-scope-options`：分公司选项接口的范围下发——`scope=write` 参数语义、服务端过滤规则、无参全量兼容。

### Modified Capabilities

- `transfer-create-pages`：写单页分公司下拉与品目点选从"全量字典/全量组织"收口为"授权范围内 × 有数可扣"；新增未选分公司时的品目入口引导。

## Impact

- **后端**：`apps/organizations/views.py`（BranchViewSet 列表按参数过滤）；`apps/assets/filters.py`（AssetStockFilterSet 加正数列筛选）；配套 pytest。
- **前端**：`api/branches.ts`（scope 参数）、`api/assets.ts`（筛选参数类型）、`components/ItemPicker.vue`（双数据源：字典/台账）、`transfers/components/TransferLinesEditor.vue`（传递分公司与扣数列上下文）、四个 PC 创建页与三个移动开单页的下拉数据源拆分；vitest + `npm run build` 门禁。
- **不动**：权限模型、单据校验逻辑、台账写入口、其他 `getBranches()` 调用方（列表筛选、组织管理、盘点创建页等维持无参全量）。
