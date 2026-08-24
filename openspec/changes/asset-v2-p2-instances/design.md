# 设计：实例层接入与领用绑实例（P2 第二刀）

## Context

第一刀已完成单头+明细行结构（TransferLine 品目 FK × 数量），台账联动按行迭代。当前实例层缺口：

- `FixedAsset`（apps/assets/models.py:157）为 V2 前旧模型：状态 在库/在用/空闲；品目信息整组手抄（资产编号/名称/类目/规格/供应商/单价/购入金额/是否租用）；`generate_internal_code` 用 count()（设计书 5.3 点名竞态）；与 TransferLine 无结构化关联
- 回收生效时按 `TransferLine.固定资产内部编号` 文本物理删除实例（transfers/views.py `_apply_ledger`，P1 注释自认过渡行为）
- `Category.management_type`（quantity/instance）已备，`manage_instances` 操作码已备（小案③），但无任何消费方
- 台账 assign 矩阵只有 在库−N（无回收库来源）；对账命令只查数量、不查实例

## Goals / Non-Goals

**Goals:**
- 实例档案一物一档：四态状态机、品目 FK、出生行追溯、锁行编号、序列号待补录
- 实例管理品目全链路绑实例：采购生成 → 领用挑（按来源）→ 归还/调拨/回收按实例流转 → 退役档案保留
- 领用库存来源（决策 #10 收尾）
- 机器执法升级：实例计数 == 台账列（实例管理品目），进对账命令与部署闸门

**Non-Goals:**
- Asset 退役与导航合并（第三刀）
- 独立处置单、盘点差异联动调整单（P3）
- 实例期初批量导入、按管理方式分级审批（P3 可选）
- 序列号格式校验/扫码硬件对接

## Decisions

### D1 状态机四态，空闲映射回收库

`在库 → 在用 →(归还)→ 在库；(回收)→ 回收库 →(再领用)→ 在用；回收库/在库 →(处置)→ 退役（终态）`。存量迁移：空闲→回收库（语义即"回收入库待再分配"）。实例不可物理删除（含后台），退役档案永久保留。

替代方案：保留三态+删除语义——被否，设计书 5.3 明确"回收/处置不物理删除"。

### D2 实例字段极简，品目信息一律联字典

保留/新增：`item` FK（PROTECT）、`内部编号`（唯一）、`序列号`（空=待补录）、`当前状态`、`使用人`/`department` FK（记录性）、`branch` FK、`birth_line` FK（→TransferLine，PROTECT，可空=存量迁移）、`入库日期`、`备注`。删除全部手抄品目列；存量行的 供应商/单价/购入金额 有值者折叠进备注前缀（`历史档案：供应商=X，单价=Y`）一次迁移。供应商/单价/采购日期对新生实例经 birth_line 派生输出（决策 #8）。

替代方案：保留文本列做"快照"——被否，铁律 1（第一刀已对单头平铺列执行同款删除，先例一致）。

### D3 行-实例关联用隐式 M2M（through 模型 `TransferLineInstance`）

`TransferLine.instances = M2M(FixedAsset, through=...)`，through 带 `unique(line, instance)`。一个实例一生会出现在多行（出生/领用/归还/…/退役），多对多是自然形状；不引入"行角色"字段——角色由单据 action_type 隐含。

替代方案：FixedAsset 上挂 last_line FK——被否，丢历史生平；per-instance 子行（数量=1 强制）——被否，与"品目×数量×实例列表"的行形状冲突且表格爆炸。

### D4 领用来源放单头，与回收去向对称

`Transfer.领用来源 ∈ {stock(新品库，默认), recycle_bin(回收库)}`。一张领用单单一来源；台账矩阵：stock → 在库−N/在用+N，recycle_bin → 回收库−N/在用+N。设计书决策 #10 原文"领用单增加库存来源"，与"回收单去向"并列，同为单据级属性。

替代方案：行级来源——被否，同一品目跨仓混领在业务上罕见，行级让选择器与校验矩阵复杂化；若真出现需求，拆两张单即可。

### D5 输入校验两段式：创建预检 + 生效终检（行锁内）

创建/编辑时（serializer + view 预检）：实例存在、品目匹配、按单据类型校验状态与分公司（assign：在库或回收库（按领用来源）且 branch=from_branch；return：在用；transfer：在库且 branch=from_branch；recovery：在用）、len(instances)==数量、品目必须为实例管理（数量管理品目携带实例即 400）。
生效时（`apply_document` 事务内 `select_for_update` 重取实例终检同一矩阵）：防止创建到生效之间实例被并发单据占用。不足/状态不符整单回滚，错误带行号定位（沿用 LEDGER_INSUFFICIENT 模式）。

### D6 实例联动收敛进 services，ledger.apply_document 仍是唯一入口

新增 `apps/assets/services/instances.py`：`generate_instances(line, branch)`（锁 InstanceSequence 行发号）、`transition(line, transfer, locked_instances)`（状态迁移）。`ledger.apply_document` 在数量变动同一事务内逐行调用。架构测试扩展：`FixedAsset` 的 save/delete/update 及 through 模型写操作仅允许出现在 `apps/*/services/`（与台账白名单同款执法）。

替代方案：实例逻辑写在 transfers app——被否，实例是 assets 域资产，且执法白名单要跨 app 收口。

### D7 内部编号 = `{品目编号}-{序号}`，InstanceSequence 锁行发号

复用第一刀 DocumentSequence 模式：`(item)` 一行，`select_for_update` 后自增。迁移时纯 Python 解析存量最大序号初始化计数（禁止数据库特定聚合——SQLite 测试全绿生产 PG 爆炸的前科）。

### D8 存量迁移四步走（每步独立迁移文件，PG DML/DDL 分离）

1. **加列**（atomic=False 拆两文件：DDL 先行、DML 回填）：FixedAsset + item FK/birth_line/department FK；Transfer + 领用来源
2. **字典存根**：资产编号不在字典的实例行自动登记存根品目（management_type=instance，名称取实例手抄名），沿用第一刀"编号户籍"先例；字典已有该编号但为数量管理 → 保持不动，实例照常挂 item，进第 4 步差异报告（管理员后续决断改管理方式或退役，对账不变量只约束实例管理品目）
3. **状态映射 + 回链 + 折叠 + 删列**（atomic=False）：空闲→回收库；回收类历史单据行按 固定资产内部编号 文本回链存活实例（已物理删除者无从回链，信息留存于审计日志）；供应商/单价/购入金额 折叠备注；删手抄列与 TransferLine.固定资产内部编号
4. **台账对齐**：实例管理品目 × 分公司，三列计数差异生成期初调整单（is_initial=True，事由"实例层接入对齐"）把台账对齐实例计数（实例档案是实物盘点过的更细粒度事实）。branch 为空的实例跳过并输出警告清单。迁移末尾跑 `check_ledger_consistency`（数量+实例双不变量）必须零差异

### D9 写接口冻结面

FixedAssetViewSet：create/update/partial_update/destroy/batch_delete/import → 405/410（与 Asset 冻结同款）；保留 list/retrieve/export；新增 `supplement` action（PATCH 序列号/备注，`manage_instances`）；新增 `timeline` action（生平=出生行信息+全部关联行倒序）。前端 FixedAssetCreate.vue 下线。存量字典存根的图片/规格补全由管理员走字典编辑，不在本刀。

### D10 生平查询走 through 反查

实例生平 = `instance.lines.all()`（through 反查）按 created_at 倒序 + 出生行派生（供应商/单价/采购日期）。不引入事件表/审计冗余（铁律 1：变动经过只存单据）。

## Risks / Trade-offs

- [PG 迁移 DML+DDL 同表 pending trigger events] → 每步拆 atomic=False 两文件（P1/第一刀既定套路），deploy.sh 迁移后对账闸门兜底
- [存量实例数量 ≠ 台账，对齐方向选错] → 对齐方向=实例计数为准（实物档案），期初调整单留痕可回溯；branch 为空/品目为数量管理的差异不自动改，输出报告人工决断
- [创建到生效之间实例被并发占用] → 生效终检在 select_for_update 事务内重验，冲突整单回滚
- [领用来源单一（单头级）限制混领] → 拆两张单可解；真有高频混领需求再修宪
- [回收文本内部编号历史信息随删列丢失] → 仅影响 P1 过渡一周内已物理删除实例的行（物理删除本身已丢档案）；审计日志仍有操作痕迹；量极小可接受
- [实例选择器在大量实例时可用性] → 列表接口已有分页/筛选（分公司×品目×状态），本刀不做扫码挑选（P3 可选）

## Migration Plan

1. 部署前全量备份（既定流程）
2. 部署顺序：代码合入 → `migrate`（四步迁移，PG 自动走 atomic=False 分片）→ `check_ledger_consistency`（deploy.sh 内置，含实例不变量）→ 前端构建
3. 回滚策略：迁移不可逆（删列）；回滚 = 恢复备份 + 回退代码。期初对齐调整单可经新调整单逆向冲正（不走数据库回滚）
4. 上线后观察：对账命令每日部署闸门 + pytest 双不变量用例

## Open Questions

- 实例期初批量导入是否需要（当前判定：不需要，存量迁移覆盖；若 P3 有诉求另立提案）
- 领用绑实例时使用人是否强制非空（当前判定：领用行使用人必填——实例绑人语义即此；serializer 校验落实）
