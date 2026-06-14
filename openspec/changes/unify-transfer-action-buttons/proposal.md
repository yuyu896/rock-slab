# 统一流转模块操作按钮样式

## 问题

### 1. 采购入库详情缺少操作按钮
- 采购入库的详情弹窗/视图中没有"审批通过"、"驳回"等操作按钮，或按钮没有正确的样式
- 审批人员无法在详情页直接操作

### 2. 领用出库、调拨按钮样式不统一
- 领用出库（AssignList.vue）和调拨（TransferList.vue）列表中的操作按钮（详情、审批、驳回）
- 与采购入库（PurchaseList.vue）的按钮样式不一致
- 需要统一视觉风格

## 影响范围

- `frontend/src/views/PurchaseList.vue` — 采购入库详情操作按钮
- `frontend/src/views/transfers/AssignList.vue` — 领用出库列表按钮样式
- `frontend/src/views/transfers/TransferList.vue` — 调拨列表按钮样式
