## Context

议题 14（2026-08-28 定案，拆案计划第 9 案）：写单页选项未收口——`BranchViewSet` 为普通 ModelViewSet，`getBranches()` 全量下发，采购/领用/调拨创建页的分公司下拉对所有人显示全部，防线仅在提交时 `validate_branches_in_scope`；`ItemPicker` 调 `getCategories`（全字典），不看所选分公司数量、不看扣数列，防线仅在提交时台账充足性校验。台账接口 `/api/assets/summary`（AssetStockViewSet）已具备：品目字段联查输出（编号/名称/规格/类目/管理方式/计量单位）、keyword 检索、DataScopeMixin 授权范围过滤——是品目收口的现成数据源。

## Goals / Non-Goals

**Goals:**
- 分公司选项接口支持 `scope=write` 服务端过滤，无参全量兼容。
- PC 四个写单页 + 移动端三个开单页：扣数方/入库方分公司下拉收口到授权范围；调拨调入方维持全量。
- PC 写单页 `ItemPicker`：扣数单据按 分公司 × 扣数列>0 过滤，显示可用数量；未选分公司禁用引导。
- 提交端校验全部保留（收口是体验优化，不是安全边界变更）。

**Non-Goals:**
- 权限模型、`resolve_user_scope`、单据校验逻辑——零改动。
- 移动端品目下拉不按台账过滤：移动端为全量字典下拉（非检索式选择器），收口需另设交互，台账充足性由提交校验兜底；如需另案。
- 其他 `getBranches()` 无参调用方（列表筛选、组织管理、权限分配、盘点创建页、`useTransferList` 等）不改——列表筛选展示全量分公司无害（结果集本身已按范围过滤）。
- 台账写入口、单据模型——零改动（提案审查两问：无信息双存，无数量直改）。

## Decisions

### D1：分公司范围下发走 branches 接口加参，不扩权限接口

`GET /api/branches?scope=write`，BranchViewSet 在 `get_queryset` 中当 `scope == 'write'` 时按 `resolve_user_scope` 过滤（`scope.all` → 不过滤；否则 `id__in=scope.branches`，空集即空列表）。理由（2026-08-28 与用户议定）：权限接口 `effective` 是管理员全员快照端点，语义不符；返回 id 集合还需二次换名称对象。无参维持全量，既有 8 处调用零改动。备选"新建 `/api/branches/write-scope` 端点"被否：一参一义更轻，避免端点 proliferation。

### D2：品目收口复用台账接口，ItemPicker 双数据源

`ItemPicker` 增加可选 props：`branch?: string`（分公司**名称**——台账筛选 `branch` 字段按 `branch__name` 过滤，与回收预检现状一致）与 `stockColumn?: '在库数量' | '回收库数量' | '在用数量'`：

- **有 `stockColumn`**：数据源切换为 `getAssetStocks({ branch, keyword, positive_column, pageSize: 50 })`，选项行附显示对应列数量（如「在库 12」）；`branch` 为空时组件禁用、占位文本"请先选择分公司"。
- **无 `stockColumn`**（采购、以及未来无台账语义的场景）：维持 `getCategories` 全量字典检索，行为不变。

备选"categories 接口加 branch+column 联查参数"被否：字典接口不应感知台账语义（铁律 1 的分层——数量信息属于台账域），且台账接口的联查输出已覆盖 ItemSummary 全部字段（`id` 取台账行的 `item` FK）。

### D3：正数列筛选做成台账 FilterSet 通用参数

`AssetStockFilterSet` 加 `positive_column` CharFilter，取值 ∈ {在库数量, 在用数量, 回收库数量}，语义为该列 >0；非法值 400（ChoiceFilter）。供 ItemPicker 用，也可服务后续"有货品目"类查询。

### D4：回收库来源剔除消耗品在前端组件层做

`领用来源=recycle_bin` 时 `TransferLinesEditor` 向 ItemPicker 传排除标记，组件对检索结果按 `managementType !== 'consumable'` 过滤。后端不加参数（消耗品×回收库的组合本身就被提交校验拒绝，此处纯 UI 提示性过滤，与创建页既有提示文案一致）。

### D5：扣数列映射收敛在 TransferLinesEditor

四页已有 `type` + `branchName` + `assignSource` props 传入 `TransferLinesEditor`；映射（assign+stock→在库 / assign+recycle_bin→回收库 / transfer→在库 / recovery→在用 / purchase→无）在 editor 内计算后传给每行 ItemPicker，页面零感知。分公司变更时 ItemPicker 依赖 `branch` prop 自动重查（`visible-change` 触发检索的既有机制不变），已选品目不强制清空（换分公司后提交校验兜底；与现状一致，不做额外清空逻辑增加复杂度）。

### D6：调拨页两下拉数据源拆分

TransferCreate / MobileTransfer 拆成两份选项：调出 = `getBranches({ scope: 'write' })`，调入 = `getBranches()`（无参全量）。采购/领用/回收（PC+移动）单下拉直接换 `scope: 'write'`。

## Risks / Trade-offs

- [分公司切换后已选品目可能失效（数量为 0）] → 提交端台账充足性校验兜底报错；回收页在用预检（第 7 案）继续按分公司联动重拉提示。不做前端强清空，避免多行场景误删用户输入。
- [无授权用户 scope=write 得空列表，页面下拉为空可能困惑] → 空列表与提交端 400 口径一致（本来就无法写单）；下拉空即"无可写单分公司"的真实反映。
- [台账行检索上限 pageSize 50，超量品目翻页不可见] → 与现状字典检索（pageSize 50）同限；品目按 keyword 检索场景足够，不做无限滚动。
- [存量 vitest mock 的 getCategories/getBranches 行为变化] → ItemPicker 无新 props 时走旧路径，既有测试不破；新增用例覆盖双数据源分支。

## Migration Plan

纯增量（接口加参 + 前端数据源切换），无数据迁移、无部署顺序依赖。回滚 = 前端还原两处数据源 + 后端参数忽略（无参行为从未变化）。

## Open Questions

无——口径已与用户议定（scope 参数方案、调拨调入全量、品目按扣数列过滤矩阵）。
