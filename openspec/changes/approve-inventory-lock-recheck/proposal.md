## Why

安全审计动态复现：创建流转单时有 `_check_inventory_lock`（分公司盘点 in_progress/pending_review 期间禁建单，复现确认创建被 400 拦截），但 **approve 动作无盘点锁复查**——行锁复查审批状态后直接 `_apply_ledger` 改台账。实测：盘点 in_progress 期间 approve 存量采购单得 200、台账 0→3 照改；且盘点 start 时已快照清单，新入账数量不在应盘清单里，**账实漂移当场成立**。创建闸与审批闸不对称，是台账完整性的实际漏洞。

## What Changes

- approve 动作在改台账前对联单两侧分公司（from_branch / to_branch）复查 `_check_inventory_lock`（None 分公司自然跳过，如采购单无调出方）
- 锁定期间 approve 返回 400（`INVENTORY_LOCKED`，与创建口径同文案同 code），台账不动、单据保持待审批，盘点结束后可正常审批
- reject / inbound_reject / update / resubmit 不动台账，不加检查（维持现状）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `inventory-concurrency-control`: 新增「盘点锁定期间流转审批必须被拒」要求（与既有审批原子性/行锁条款同族，补齐创建/审批对称性）

## Impact

- `backend/apps/transfers/views.py`：approve 路径（`transaction.atomic` 内、`_apply_ledger` 之前）补两侧分公司盘点锁复查
- `backend/tests/`：新增锁定期间审批被拒用例（台账不动、单据不流转）与解锁后可批回归
- API 行为变化：盘点锁定期间 approve 从 200（台账照改）变 400；审批人重试即可，无数据迁移
- 无迁移、无前端改动（前端对 400 已有统一错误展示）
