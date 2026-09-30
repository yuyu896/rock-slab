## Context

`_check_inventory_lock`（backend/apps/transfers/views.py:104-128）按 branch_id/name 查 `InventoryTask.status__in=_INVENTORY_LOCKED_STATUSES`，命中抛 ValidationError（code=INVENTORY_LOCKED）；目前仅 `_create_action`（约 212-213 行）对 from/to 两侧调用。approve（约 274-319 行）流程：`_assert_transfer_operable` → `transaction.atomic` 内 `select_for_update` 重取单据并复查审批状态 → `_apply_ledger`。盘点 start 快照清单后，任何台账变动都不在应盘集合内——审批放行即制造账实差异。

## Goals / Non-Goals

**Goals:**

- 盘点锁定期间（in_progress/pending_review），联单任一侧分公司的 approve 被拒（400），台账与单据状态不变
- 与创建闸同 code 同文案，审批人可理解、可重试

**Non-Goals:**

- 不动 reject/update/resubmit/inbound_reject（不改台账；inbound_reject 零台账影响是既定设计）
- 不解决「盘点 start 前已存在的待审批单在 start 时未提示」的流程问题（审批侧拦住即保证账实，流程提示属 UX 另案）
- 不动盘点侧自身的调整单生成（盘点 approve 的差异调整是盘点闭环的一部分）

## Decisions

**1. 检查点：approve 的 `transaction.atomic` 内、`_apply_ledger` 之前，对两侧分公司各调一次 `_check_inventory_lock(branch_id=…)`。**
复用现成闸门（同 code/文案，前端与调用方零新概念）。`branch_id=None` 时函数自身短路（`if branch_id:` 分支），采购单（from_branch=None）自然只查调入方，无需条件判断。放在 atomic 内：抛错即整体回滚（本就无写入），行锁释放，语义干净。

**2. 只加在 approve，不加在 reject。**
reject 不触碰台账；盘点期间驳回单据是安全且合理的运营动作（例如驳回后盘点更干净）。保持面最小。

**3. 不做「start 时拦截存量待审批单」的反向方案。**
在盘点 start 时强制清空/警告存量待审批单，会引入新的流程耦合（start 可能因他司在途单而失败）；审批侧拦截已足够保证台账与盘点快照一致。

## Risks / Trade-offs

- [盘点期间待审批单积压，审批人需在盘点结束后重试] → 与创建侧既有体验一致；盘点通常短周期；400 文案明确指向「分公司正在盘点」
- [长事务中多一次 InventoryTask 存在性查询] → 走 branch 索引的存在性检查，代价可忽略；审批频度低

## Migration Plan

纯代码，无迁移。部署即生效；回滚 revert。上线验证：in_progress 盘点期间审批任一涉及该分公司的单据应得 400 INVENTORY_LOCKED；盘点完成后同一单据可正常审批通过。
