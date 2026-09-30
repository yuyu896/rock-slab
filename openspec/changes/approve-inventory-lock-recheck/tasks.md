## 1. 实现

- [x] 1.1 `backend/apps/transfers/views.py` 的 approve 动作：`transaction.atomic` 内、`_apply_ledger` 之前，对 `locked.from_branch_id` 与 `locked.to_branch_id` 各调 `_check_inventory_lock(branch_id=…)`（None 分支函数自身短路）

## 2. 测试

- [x] 2.1 新增 `tests/test_approve_inventory_lock.py` 4 例：采购单锁定期间 400（台账零变动、单据仍待审批）；调拨单调入侧锁定 400（两侧库存不变）；无关分公司盘点 200；盘点完成后重批 200 且台账正确
- [x] 2.2 全量 `pytest` 通过（884 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（盘点期间审批入口应得「正在进行盘点」提示，盘点完成后可正常审批）

> 手验要点：建一张采购待审批单 → 该分公司开盘点并 start → 审批应得「分公司『xx』正在进行盘点」400；盘点审批完成后重批同一单应成功入账。
