## Context

P1 立契约时盘点被定为记录模式（spec `inventory-item-basis`「盘点差异为记录模式」明文"P3 交付差异自动生成调整单，期间由持 adjust_ledger 者手工开单"），本变更是该契约的到期兑现，也是 P3 验收标准本身。

现状关键事实：

- 盘点审批钩子已就位：`inventories/views.py` `_transition` 在 `select_for_update` 锁任务行的事务内调 `before_save`，其内 raise ValidationError 整笔回滚返回 400；approve 的 `_adjust` 目前只有时间戳（views.py:194）。
- 差异行可枚举：`InventoryItem.result ∈ {surplus, missing}` 即差异（matched 不动）；提交时漏盘规则（zero）已把漏盘项写成 `actual=0/result=missing`，keep 规则下保持 `unchecked`。应盘取台账行在库数量（`_generate_items`），盘点只盘在库列。
- 调整单唯一写入口 `ledger.apply_adjustment(branch, item, column, delta, reason, operator, is_initial)` 现成：事务 + 行锁 + 负数拒绝（LEDGER_INSUFFICIENT）。
- `LedgerAdjustment` 缺单据编号与来源追溯；手动开单 API（`/api/assets/adjustments` create，`adjust_ledger` 门禁）无审计；前端无任何调整单界面。
- 发号器 `transfers.DocumentSequence`（action_type 无 choices 约束）+ `generate_document_number(action_type, doc_date)` 可直接复用。

## Goals / Non-Goals

**Goals:**
- 盘点审批通过 → 差异自动开调整单 → 台账同步修正，全程在锁内事务内，铁律 2 不破（只经 `apply_adjustment`）。
- 调整单成为完整单据：编号、来源任务、审计、前端可见可开。
- 差异不足时整笔审批失败回滚，差异永远暴露不吞掉。

**Non-Goals:**
- 调整单审批流（见决策 D2，落定为不设）。
- 报表口径切换、待补录提醒（P3 后续刀）、处置单（用户决断：留待真实需求）。
- 盘点在用/回收库列（盘点范围仍是在库列，与既有 `_generate_items` 一致）。
- 通知契约变更（只在 completed 通知 extra_data 附调整数，属增强）。

## Decisions

**D1 差异开单挂在 approve 的 `before_save` 钩子内，逐行调 `apply_adjustment`**
钩子已在 `select_for_update` 任务行的事务内；`apply_adjustment` 内层 `transaction.atomic` 成为保存点，任一行失败整体回滚——任务留在 pending_review、台账不动、零调整单残留。替代方案（审批后异步/信号开单）被否：脱离事务就有"审批成功但开单失败"的中间态，违反对账精神。
经办人=审批人（request.user）；事由模板：`盘点差异「{task.name}」：在库 {expected} → {actual}（{盘盈|盘亏}{|delta|}）`；目标列=在库数量；变动量=actual−expected。无差异行则不开任何单（不产空单）。

**D2 调整单不设审批流，创建即生效落案**
docstring"P3 按需补充"就此结案。理由：盘点路径的审批由盘点任务自身承担（开单只是执行已审结论）；手动路径与台账增量导入路径同级——导入也是"预览确认即入账"，同级路径同级待遇。防线=权限（`adjust_ledger`）+ 审计 + 单据留痕，再加一层审批只制造状态机负担。

**D3 编号复用 `DocumentSequence`，前缀 TZ，assets→transfers 延迟导入**
`generate_document_number('adjust', date)`，`DOC_NUMBER_PREFIXES` 加 `'adjust': 'TZ'`。`transfers.services` 模块级只依赖自身 models，assets 侧在函数内延迟导入，无环。替代方案（调整单自建序号表）被否：两套发号器两套防重号逻辑，无收益。日期取 `timezone.now().date()`。

**D4 来源任务 FK：`source_task` nullable + `on_delete=SET_NULL`，不做唯一约束**
一次 approve 产多张调整单（每差异行一张），是 1:N 不是 1:1，不能唯一。幂等由状态机保证：`pending_review → completed` 单向一次，approve 不可能重入双开。任务删除（PROTECT 语义下本不发生）降级为 NULL，编号与事由仍可追溯。

**D5 存量回填编号：纯 Python 逐行发号，DDL 与 DML 拆迁移文件**
存量行少（生产导入期初+日常少量），逐行 `generate_document_number` 按 created_at 顺序回填，禁 min(uuid)/数据库聚合（SQLite 测试全绿生产 PG 爆炸的前科）。AddField（nullable）与回填拆两个迁移文件，规避 PG"同事务 DML+DDL 同表"的 pending trigger events 前科；回填纯 DML 保持默认原子，可独立重跑（按 编号 IS NULL 过滤）。

**D6 不足即失败的信息必须可定位**
`_apply_delta` 的报错（分公司×品目、当前量、变动量）在钩子内原样上抛，审批人看到具体哪行差多少；处置路径=驳回重盘或先手工平账。绝不静默跳过差异行——跳过=把漂移写回系统，P1 立契约就是治这个。

**D7 前端三处落点全走既有形态**
台账行内"调整"弹窗（预填分公司×品目，目标列/变动量/事由三项）；"调整记录"列表弹窗（编号/时间/分公司/品目/列/±量/事由/经办人/来源，Excel 式朴素表格无徽章）；盘点审批确认弹窗列差异预览（编号、在库 X→Y、±N）——先看后批，避免"批完才发现动了账"。api 层 `listAdjustments/createAdjustment` 走既有 request 实例。

## Risks / Trade-offs

- [审批时台账已被流转单变动，差异调整致负数] → 整笔回滚报 400，信息定位到行；审批人驳回重盘或先平账。低频（盘点窗口内同品目大额流转才触发），暴露优于吞掉。
- [存量回填迁移在 PG 上跑] → 拆 AddField/回填两步、回填幂等可重跑、deploy.sh 对账命令兜底；编号唯一约束在建回填完成后再加（或回填迁移内最后一步 ALTER）。
- [approve 语义从"只记录"变"动账"，存量用户肌肉记忆] → 审批确认弹窗明示"将生成 N 条调整单修正台账"，报告页展示已生成数；审计留痕。
- [资产 app 反向依赖 transfers 发号器] → 函数内延迟导入，架构测试不涉足；若未来调整单迁出 assets，发号器随之搬迁。

## Migration Plan

1. 迁移一：AddField（`单据编号` nullable unique、`source_task` FK nullable）。
2. 迁移二：纯 Python 回填编号（atomic=False 不需要——纯 DML 无 DDL，保持默认原子即可；按 created_at 升序逐行发号）。
3. 部署顺序无特殊要求（新列全 nullable，旧代码兼容）；部署后跑 `check_ledger_consistency`（口径未变，应零差异）。
4. 回滚：字段可空、无破坏性变更，回滚代码即可；已生成的盘点调整单是合法流水，无需清理。

## Open Questions

无——审批流（D2）、处置单、分级审批均已拍板（分级审批保持挂起，处置单留待真实需求）。
