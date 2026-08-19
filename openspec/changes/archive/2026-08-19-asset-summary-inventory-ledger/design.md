## Context

- 资产汇总现状（inventory-menu-rework 交付）：`AssetViewSet.summary` action（`GET /api/assets/summary`）对 `Asset` 按 `branch` 聚合返回数组，前端 `views/assets/AssetSummary.vue` 纯展示（无筛选/分页/编辑）。
- `Asset`（资产明细，品目级）自带 数量/警戒线/是否充足；`FixedAsset`（固定资产，实例级）一记录一台实物。领用/归还/调拨/采购 通过 `TransferViewSet._sync_asset` / `_apply_warehouse_stock` 联动 Asset 数量；**回收（recovery）目前无 sync handler，不扣任何库存**。
- 回收入口现状：`/transfers/recovery` 列表页 + `RecoveryCreate.vue`（创建待审批单）；明细/固定资产列表行内无回收操作。
- 所属部门现状：`AssetCreatePage.vue` / `AssetEditDrawer.vue` 均为自由文本 `<input>`。
- 路由坑：`apps/assets/urls.py` 的 `DefaultRouter(trailing_slash=False)` 以 `r''` 注册 AssetViewSet，新增路由前缀必须排在其前，否则被吞。

## Goals / Non-Goals

**Goals:**
- 资产汇总成为独立库存台账（新表）：完整列表页（10 列表头、分页序号、筛选、增删改、导入导出）。
- 台账行内「填入」：预填字段创建资产明细/固定资产记录，不扣台账库存。
- 回收联动台账：行内直接回收即时生效；回收页/导入单据审批通过后生效；扣台账库存并重算是否充足；明细数量同步扣减；固定资产实例记录删除。
- 资产明细表单所属部门：预置 5 项 + 自定义输入。

**Non-Goals:**
- 采购/领用/归还/调拨不改——仍只联动资产明细数量，不联动台账（后续观察再定）。
- 不改移动端布局、不改路由路径与权限模型框架（复用 DataScopeMixin/OperationPermission）。
- 固定资产回收不涉及台账以外的固定资产批量删除逻辑；回收页手建单据不含固定资产实例定位（无内部编号时不删 FA 记录）。
- 台账不与品目（Category）强关联：类目/分类/名称按模板自填，不校验品目登记。

## Decisions

### D1. 新模型 `AssetStock`（库存台账），键=分公司+资产编号
**字段**：`分公司`、`分公司编号`、`branch` FK（模式照抄 Asset）、`资产编号`、`资产类目`、`物品分类`、`资产名称`、`规格`、`数量`、`警戒线(null=True)`、`是否充足`；继承 UUIDModel+TimestampedModel。约束：`unique_together('分公司', '资产编号')`。无 `序号` 字段——展示序号是分页序号（AssetList.vue:489 的 `(page-1)*pageSize+index+1` 模式），与 Asset 持久化序号无关。
**是否充足**：模型 `save()` 内强制重算 `是否充足 = (警戒线 is None) or (数量 >= 警戒线)`，不信任客户端传值（导入/编辑/回收扣减统一生效）。
**备选**：复用 Asset 表加"是否台账行"标记。未选：一张表两种语义，导入去重键/权限/序号规则互相打架；独立表迁移清晰、旧数据零风险。

### D2. 路由：`summary` ViewSet 注册在 `r''` 之前，替代旧聚合 action
**选择**：`AssetViewSet.summary` action 删除；新建 `AssetStockViewSet(DataScopeMixin, ModelViewSet)`，`router.register(r'summary', ...)` 排在 `register(r'', AssetViewSet)` 之前。接口面与 FixedAssetViewSet 对齐：list（分页+筛选 分公司/类目/关键词）、create/update/destroy、batch-delete、template、import、export。
**BREAKING**：`GET /api/assets/summary` 从聚合数组变为 `{count,next,previous,results}` 分页台账，前端同版本替换，无其他消费方。
**权限**：读取=登录用户（数据范围过滤，`scope_branch_field='branch'`）；写操作（create/update/destroy/batch_delete/import）=`manage_assets`（与 FixedAssetViewSet 的 required_operations 一致）。

### D3. 导入模板 8 列，去重键=分公司+资产编号，已存在即报错
**模板列**：`分公司 资产编号 资产类目 物品分类 资产名称 数量 规格 警戒线`（序号自动分页、是否充足自动计算）。校验沿用资产明细导入：`validate_excel_upload/validate_row_count`、分公司合法性（`branch_validation_error`）、≤200 行、按表头列名映射。表内与 DB 去重键均为 `(分公司, 资产编号)`，命中报"已存在，请编辑该行"。
**备选**：同键累加（补货语义）。未选：误重导会静默翻倍库存，报错更显式；补货走编辑。
**种子迁移**：模型迁移后附 data migration，按 `Asset` 现有数据聚合 `values('分公司','资产编号',...).annotate(Sum('数量'))` 生成台账初始行（类目/分类/名称/规格取首行，警戒线取该组 max），保证存量连续。

### D4. 「填入」为纯前端组合，复用现有 create 接口
**选择**：台账行内「填入」按钮 → `SummaryFillDialog`：单选填入资产明细/固定资产，预填 分公司/资产编号/资产类目/物品分类/资产名称/规格（明细另带警戒线），用户补 所属部门/使用人/数量/入库日期 等，提交调既有 `POST /api/assets/`（createAsset）或 `POST /api/assets/fixed-assets`（createFixedAsset，内部编号自动生成）。**不扣台账库存——创建接口本来就不动台账，无需后端改动**。
**理由**：明细/固定资产是"说明性"记录，台账是唯一库存账；复用创建接口即复用全部校验（品目登记校验、必填校验）。
**注意**：明细 create 校验"资产编号须在品目登记"，填入的台账编号若未登记品目会被拒——弹窗内提示该错误即可（错误信息已友好）。

### D5. 回收联动：`approve()` 显式分支，统一 `_apply_recovery_stock`
**选择**：`approve()` 内对 `ACTION_RECOVERY` 显式分支调用 `_apply_recovery_stock`（不挂 `_sync_asset` 的 sync_map——其 handler 以「先查到 Asset 记录」为前提，明细无记录的纯固定资产回收会整体跳过台账扣减）；`_apply_recovery_stock` 在事务内按序执行：
1. **台账扣减**：`AssetStock` 匹配 `(分公司=调出分公司, 资产编号)`（优先 branch FK 匹配，回退名称）→ `数量=max(0, 数量-调拨数量)`，save 时自动重算是否充足；无匹配行则跳过（与现有 _sync_asset 容错一致）。
2. **明细扣减**：`Asset` 匹配优先 `(分公司, 资产编号, 所属部门=调出部门)`（明细同键可多行），回退 `(分公司, 资产编号)` 首行 → `数量=max(0, 数量-调拨数量)`，**clamp 0 保留记录**（沿用 assign/return 语义，不删行）。
3. **固定资产删除**：Transfer 新增可选字段 `固定资产内部编号`（CharField, blank）；非空则删除对应 `FixedAsset` 记录（数量 1 实例回收后记录消失）。
**生效时机**：回收页/Excel 导入创建的单据=待审批，`approve()` 通过时触发（走既有"退回/调拨/回收等：直接同步"分支）；**行内直接回收=即时生效**（见 D6）。

### D6. 行内直接回收：`immediate` 参数 → 创建即「已通过」并同事务联动
**选择**：`AssetList.vue` / `FixedAssetList.vue` 行内新增「回收」按钮（`canManageAssets` 可见）→ `RecoveryDialog`（明细：数量≤该行数量、回收分类、出库日期、存放位置、备注；固定资产：内部编号随行传入、数量固定 1）→ `POST /api/transfers/recovery` 携带 `immediate: true` + `固定资产内部编号`（FA 时）。
后端 `_create_action` 扩展：`immediate` 且 action=recovery 且用户持 `manage_assets` 时，事务内：创建 Transfer（`审批状态='已通过'`、审批人=操作者、审批时间=now）→ 调 `_apply_recovery_stock`（D5 逻辑抽取为可复用函数，approve 路径与 immediate 路径共用）；仍受 `_check_inventory_lock` 盘点锁约束。无 `manage_assets` 传 immediate → 400。
**备选**：行内回收也走待审批。未选：用户语义是"编辑物品回收后库存即减少、FA 记录即消失"；操作者已持 manage_assets，加审批徒增摩擦。审计：复用 `@audit_log(action='recovery')`，回收单落回收列表可追溯。

### D7. 所属部门：`DepartmentSelect` 组件（原生 input + datalist）
**选择**：新组件 `components/DepartmentSelect.vue`：`<input list=...>` + `<datalist>`，选项来自 `constants/index.ts` 新增 `DEPARTMENT_PRESETS = ['仓库','行政部','人事部','财务部','业务部']`；可输入任意自定义值（v-model 直传字符串）。替换 `AssetCreatePage.vue` 与 `AssetEditDrawer.vue` 的所属部门 input。
**理由**：纯 CSS/原生风格与现有表单一致（这两处均为原生 input），零依赖零状态；Element Plus `el-select allow-create` 也能做，但为两个表单引入不必要组件层级。不持久化自定义项（下次手输即可），保持无后端改动。
**范围**：仅资产明细两个表单；固定资产/回收/汇总表单的自由文本不动（按用户确认）。

### D8. 前端页面结构
- `AssetSummary.vue` 重写：结构对齐 AssetList（页头+筛选[分公司/资产类目/关键词]+表格+BasePagination+批量导入/导出/新增）；表头 10 列；是否充足列用 是/否 badge（不足红）；行操作=编辑/填入/删除。
- 新增 `views/assets/SummaryEditDrawer.vue`（新增/编辑台账行）、`SummaryFillDialog.vue`（D4）、`SummaryImportDialog.vue`（模式照 AssetImportDialog：模板下载+上传+行级错误展示）、`views/assets/RecoveryDialog.vue`（D6，明细/固定资产两处复用）。
- `api/assets.ts`：`getAssetSummary` 删除，新增 `getAssetStocks/createAssetStock/updateAssetStock/deleteAssetStock/batchDeleteAssetStocks/importAssetStocks/exportAssetStocks/downloadAssetStockTemplate`；`api/transfers.ts` 的 `recoverAsset` 增加 `immediate/固定资产内部编号` 透传。`types`：`AssetSummaryRow` → `AssetStock`。
- 路由 `/assets/summary` 与菜单「库存→资产汇总」位置不变。

## Risks / Trade-offs

- [`r''` 路由遮蔽 `summary` 前缀] → 注册顺序写死在前，pytest 路由测试覆盖 list/create/import 端点。
- [新旧接口同 URL 语义突变（聚合数组→分页对象）] → 仅本前端消费，前后端同一 commit/release；vitest 更新 API 层测试。
- [种子迁移把"使用中/维修中"明细也计入台账] → 台账定位是账面库存，含全部状态合理；若用户后续要区分，可编辑台账行调整。
- [回收时台账无匹配行（编号未导入台账）] → 跳过不报错，回收单仍成功；明细侧照常扣减，两账不强制一致。
- [immediate 回收绕过审批被滥用] → 双重门槛：manage_assets + 盘点锁；审计日志与回收列表留痕。
- [明细同键多行时回收扣错行] → 优先按调出部门精确匹配；回退首行仅影响说明记录的数量，台账扣减不受影响。
- [导入同键报错造成批量导入中断体验] → 沿用行级错误聚合（merge_errors），其余行照常导入。

## Migration Plan

1. 后端两个迁移：`apps/assets` 新增 `AssetStock` 表+种子 data migration；`apps/transfers` 新增 `固定资产内部编号` 字段。
2. 部署走 `deploy.sh`（migrate 自动执行）；前后端同版本发布。
3. 回滚：git revert 后 `migrate` 回滚两个迁移（种子数据可重建，无外部依赖）。

## Open Questions

（无——表头/联动语义/入口/部门范围均已与用户确认。）
