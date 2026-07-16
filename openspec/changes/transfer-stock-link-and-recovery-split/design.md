## Context

- `_sync_asset` 用 `Asset.objects.filter(资产编号=X).first()` 查资产——**不区分分公司**。
- `_sync_assign`：仅改状态，不扣数量。
- `_sync_transfer`：仅挪 branch，不分数量。
- 回收在「资产流转」菜单子项下。

## Decisions

### 决策 1：_sync_asset 改为按分公司查
- filter 改为 `filter(资产编号=X, branch=from_branch)`。

### 决策 2：领用——校验库存 + 扣减
- 审批通过前校验：调出分公司该资产数量 >= 调拨数量；**不足则报错拒绝**（「资产 XXX 库存不足」）。
- 通过后：`数量 -= 调拨数量`，状态改「使用中」。

### 决策 3：调拨——调出扣减、调入增加
- 调出：`数量 -= 调拨数量`。
- 调入：同编号存在则 `数量 += 调拨数量`；不存在则新建。

### 决策 4：回收菜单独立（仅前端）
- 回收从「资产流转」子菜单移出，成为一级菜单。
- 后端不变（Transfer action_type='recovery'），路由保持 `/transfers/recovery`。
- 回收的业务逻辑后续单独改。
