## Context
- PurchaseDetail.vue 已实现：独立详情页 + 已驳回编辑（全字段）+ 重新提交（resubmit）。
- AssignList/TransferList 用弹窗看详情（viewDetail/showDetailModal），无编辑能力。
- 后端 resubmit（已驳回→待审批）和 perform_update（限已驳回可改）是通用的，不区分类型。

## Decisions

### 决策 1：复用 PurchaseDetail 模式
- AssignDetail/TransferDetail 页面结构、编辑表单、重提逻辑参照 PurchaseDetail.vue。
- 字段差异：领用有使用人/用途；调拨有调出/调入分公司/部门/负责人。

### 决策 2：AssignList/TransferList 详情按钮改跳转
- 移除弹窗（showDetailModal/detailItem/viewDetail），详情按钮改 `router.push`。
- 与 PurchaseList 已做的改造一致。

## Open Questions
（暂无。）
