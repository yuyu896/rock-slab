## Context

- 现状盘点链路：`InventoryTask(branch × category + 规则)` → start 时 `_generate_items` 从 AssetStock 生成 `InventoryItem(task×stock, expected=在库数量)` → check/导入写 actual → submit 应用漏盘规则 → approve 时 `generate_variance_adjustments` 逐差异项经 `ledger.apply_adjustment(column=在库数量)` 开调整单（唯一写入口，铁律 2）。
- 回收库列（`AssetStock.回收库数量`）与在用列并存；台账调整单 `目标列` 本就支持三列，只是盘点路径写死在库列。
- `FixedAsset` 实例有 `当前状态/使用人(记录性文本)/department(FK)/branch(FK)/内部编号(unique)/序列号`；`Department` 是分公司×部门名字典（非组织树节点）。实例管理品目才有实例（数量管理品目无档案层，铁律 1）。
- 盘点状态机与并发控制（行锁 + 二次状态校验）在 `_transition` 内统一处理，实例盘复用同一状态机。
- 回收单创建已有独立页面（RecoveryCreate，含在用预检，修订 1.3）；行结构 `品目×数量×instances(M2M)`。

## Goals / Non-Goals

**Goals:**
- 台账盘支持库别（在库/回收库），应盘与差异修账跟随对应列。
- 部门实例盘：任务选部门 → 在用实例快照清单 → 分组逐台打钩/扫码 → 提交审批 → 完成不改账，盘亏待跟进可一键发起回收单。
- 创建页方式切换 + 重复规则场景提示（设计书十三节明文）。
- 报告/导出覆盖两种盘点口径。

**Non-Goals:**
- 不改台账盘点既有状态机、并发控制、Excel 导入模板结构。
- 不新增"在用列"台账盘（在用核对由实例盘承担，语义已在设计书定案）。
- 盘亏不自动生成任何单据（人工决定；一键回收也只是预填创建页，仍走审批）。
- 移动端不做实例盘的分组清单编辑视图，仅扫码/手动输入内部编号打钩（分组清单在 PC 端）。
- 不做跨部门实例盘（任务单部门；跨部门拆多任务）。

## Decisions

1. **盘点类型用 `department` 是否为空判定**，不另设 type 字段：`department = null` → 台账盘（branch × category × stock_bin）；`department ≠ null` → 实例盘。两维正交于一个任务，避免第三种"类型"字段与字段组合打架。
2. **`stock_bin` 只作用于台账盘**（choices: stock/recycle，默认 stock）。实例盘固定盘"在用"实例，库别无意义，序列化器对实例盘忽略该字段。
3. **实例盘清单 = start 时的实例快照**（新模型 `InventoryInstanceItem(task, instance, result, checked_by/at, remarks)`，unique(task, instance)）。快照语义与台账盘一致（生成后不追实物变动）；逐台核对是布尔结果，无 qty 字段。不复用 InventoryItem——qty/expected/stock 语义不匹配，混用会让所有下游分支翻倍。
4. **实例核对动作 `check_instance`**：`{instance_id, found: bool, remarks}` → result ∈ {matched, missing}，记录 checked_by/at；重复核对允许覆盖（后者为准），check_count 累计留审计。扫码打钩 = found=true 的同一动作（前端按内部编号/序列号定位 instance_id）。
5. **漏盘规则复用于实例项**：`zero` → 提交时未核对实例置 missing（进入缺失明细）；`keep` → 保持 unchecked（报告单列"未核对"）。不新造规则字段。
6. **实例盘 approve 不生成调整单**：`generate_variance_adjustments` 仅对台账盘任务调用。审批动作、状态机、驳回重盘全部复用；recount 的 reset 对实例项同样适用（reset result→unchecked）。
7. **盘亏一键回收 = 预填跳转，不做后端代客开单**：报告视图按钮携带 `taskId` 跳转回收创建页，页面拉取缺失实例预填明细行（品目聚合数量 + instances），操作者补单头后走既有创建/审批流。理由：回收单创建的校验（在用预检、去向必填）与审计语义都在既有路径上，后端另开代客入口会复制业务规则（违背单一入口）。
8. **台账盘行集收紧为"该列>0"**：现状生成"任一列>0"的行但应盘取在库列，列=0 的行是噪音；改为按目标库别列过滤，报告更干净，盘亏误报减少。实例盘清单天然非空行（在用实例）。
9. **`_apply_missed_rule`、progress、report、export 按任务类型分支**：progress 的 checked/matched/… 计数对实例项同口径复用（matched/surplus/missing/unchecked 五态中 surplus 对实例不可能出现，保留字段不影响）。
10. **前端创建页**：方式 radio（台账盘点/部门实例盘点）；台账盘点显示库别下拉；实例盘点显示部门下拉（按已选分公司过滤，复用 DepartmentSelect 组件口径）+ 说明文案（仅实例管理品目/逐台核对/差异不自动改账）；重复规则选项旁挂场景提示 tooltip/文案。

## Risks / Trade-offs

- [实例快照与实物漂移：任务期间实例被领用/回收，报告与档案不符] → 快照语义明确写入任务说明（报告注明"清单为开始盘点时快照"）；差异处置走人工跟进，不改账。
- [部门字典与实例 department 可能为空（记录性字段允许空）] → 实例盘清单只含 department=任务部门的实例，无部门实例不出现在任何部门盘（提示文案说明）；如需全量在用盘，用台账盘在用列口径另案（非目标）。
- [回收库盘的漏盘清零(zero)误伤] → 与在库盘同规则同确认交互，审批人看差异清单后通过；清零只改回收库列，账可由调整单追溯。
- [InventoryItem 与 InventoryInstanceItem 双表增加页面/接口分支复杂度] → 集中在 task 序列化器输出 `inventoryKind`（'stock'|'instance'）单字段供前端分支，避免前端自行推断。
- [存量进行中任务无 stock_bin] → 默认 'stock' 与原行为逐字节一致（应盘在库列、修在库列），无迁移数据风险。

## Migration Plan

1. 后端 migration（纯 DDL：AddField stock_bin/department + CreateTable inventory_instance_item）随部署自动执行，对存量无行为变化。
2. 前端新字段均为可选输入，旧客户端（缓存页面）创建的任务走默认值。
3. 回滚：代码回滚即可；新表/新列为增量，无数据回填。
