## Why

安全审计动态复现两个缺陷：① `import_excel` 的 confirm 分支逐行调 `ledger.apply_adjustment`，每次调用独立事务、循环外无整体 atomic——中途任一行失败，前面行已提交，留下部分调整与残留调整单（复现：行2 失败后行1 已落库）；② 差量 `delta` 用解析阶段读的现值快照计算（views.py:174-176），apply 时不复核锁定行当前值——并发窗口内有他方变动（采购/流转/另一导入）时终值偏离导入目标（复现：注入 +100 后 confirm，终值 110 ≠ 目标 10，调整单事由还写着「在库 0 → 10」的过时口径）。

## What Changes

- `ledger.py` 新增导入确认唯一入口 `apply_import_adjustments(entries, operator)`：整体 `transaction.atomic` + 按 (branch, item) 全局序**先锁齐**台账行（复用 `apply_document` 的防死锁范式）+ 锁内**复核现值 == 解析期快照**，不符抛 `IMPORT_STALE`（400，带行号定位）整体回滚
- `views.py` confirm 分支改为纯调用（不再逐行 apply），维持「台账唯一写入口」铁律与架构测试口径
- 调整单事由在复核通过后生成，数值口径真实

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `ledger-single-source`: 「台账增量导入为存量初始化唯一入口（差异预览 → 确认生成期初调整单）」条款补齐原子性与现值复核要求

## Impact

- `backend/apps/assets/services/ledger.py`：新增 `apply_import_adjustments`（锁齐 → 复核 → 逐行 `_apply_delta` → 调整单留痕，一个事务）
- `backend/apps/assets/views.py`：confirm 分支替换为调用新入口
- `backend/tests/test_write_scope.py` 或新文件：新增整体回滚、现值漂移拒单、正常确认回归用例
- API 行为变化：confirm 失败从「部分应用」变「全部回滚 + 400 IMPORT_STALE」；成功路径响应结构不变（applied/errors）
- 无迁移、无前端改动（400 统一错误展示）
