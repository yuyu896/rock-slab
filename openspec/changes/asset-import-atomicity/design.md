## Context

`import_excel`（backend/apps/assets/views.py:191-228）两阶段：解析产 diffs（含解析期现值快照 `现值` 与 `变动量 = 导入值 - 现值`）→ confirm=1 逐行 `ledger.apply_adjustment`（每调用自带 `transaction.atomic`）。`ledger.apply_document` 已示范正确范式：按 (branch,item) 全局序一次性 `select_for_update` 锁齐再逐行变动，外部事务整体回滚。铁律 2 要求台账写全部走 `services/ledger.py`（架构测试执法）。

## Goals / Non-Goals

**Goals:**

- confirm 全有或全无：任一行失败（含现值漂移）→ 全部回滚，无部分调整、无残留调整单
- 并发安全：解析→确认窗口内的他方台账变动被检出（IMPORT_STALE 400），终值绝不偏离导入目标
- 调整单事由数值与真实应用前值一致

**Non-Goals:**

- 不改解析/差异预览逻辑（含范围校验、实例品目拒绝、表内去重）
- 不引入导入会话持久化/二次确认 token（现值复核已保证正确性，会话化属 UX 另案）
- 不处理流转 Excel 导入的指纹竞态（另案）

## Decisions

**1. 新入口 `apply_import_adjustments(entries, operator)` 放 ledger.py，views 纯调用。**
铁律 2 的写白名单在 ledger.py 扩一项，架构测试口径不变（views 不触台账模型写）。签名收 entries（即解析产物 dicts），返回 applied 数。

**2. 锁序复用 apply_document：按 `(branch.pk, item.pk)` 排序一次 `select_for_update` 锁齐，再逐行复核+变动。**
与流转审批的加锁顺序全局一致，交叉并发（导入确认 × 单据审批）不会环形等待。行不存在则内存建行（同 `_locked_row(create=True)` 语义）。

**3. 现值复核语义：锁定行当前值 ≠ 快照 `现值` → `ValidationError({'code': 'IMPORT_STALE', 'detail': 第 N 行（编号 @ 分公司）：解析时 X，当前 Y，请重新上传})`。**
导入为**无状态两阶段**：confirm 请求内重新解析文件、快照取自同一请求的解析阶段——竞态窗口即「解析（无锁读）→ 应用（加锁写）」之间，多行导入的行1 读数与行N 应用间隔更长。不静默重算差量——用户确认的预览是「从 X 到 Y」，底层已变就该重新走预览；静默重算会让留痕事由与确认内容脱节。复核通过后 `_apply_delta(row, COLUMN_STOCK, 变动量)` 与 `LedgerAdjustment.objects.create(事由=…现值→导入值…)`，事由真实。跨请求重传同文件因无状态重解析差量为零，自然幂等（applied=0）。

**4. 负值目标仍由 `_apply_delta` 拒绝（LEDGER_INSUFFICIENT），在整体事务内 → 自然全量回滚。**
解析端不重复加目标非负校验（单一闸门，行为与现状一致）。

## Risks / Trade-offs

- [大文件导入的锁持有时间变长（锁齐全部行再逐行）] → 单分公司日常导入行数量级小；且流转路径同范式已验证
- [IMPORT_STALE 要求用户重新上传（而非自动重算）] → 明确的「重新预览」语义，避免确认内容与实际变动不符；错误信息带行号定位
- [解析与确认间分公司/品目被删除等极端情况] → 锁查不到行按 0 处理或自然报错，不劣于现状

## Migration Plan

纯代码，无迁移。部署即生效；回滚 revert。上线验证：同一文件连传两次（第二次现值已变）应得 IMPORT_STALE 400 且台账无第二次变动。
