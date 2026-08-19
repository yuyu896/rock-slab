## Context

- 采购入库「详情」现为模态弹窗（`PurchaseList` 的 `showDetailModal`/`detailItem`，来自 `useTransferList.viewDetail`）。
- `TransferViewSet` 为 `ModelViewSet`，有 `update`/`partial_update`，且未列入 `required_operations`（即当前任意登录用户可改自己数据范围内的流转）。
- 采购入库提交按 `order.items` 逐条 `purchaseAsset` 创建 transfer（**每物品一条 transfer，无聚合订单**）；`PurchaseList` 逐条展示。
- `AssignCreate.vue` 为单物品表单；`PurchaseCreateForm.vue` 为多行物品表单（可参照）。
- 路由：`transfers/purchase`（列表）、`transfers/purchase/create`（新建）、`transfers/assign/create`（领用新建）。

## Goals / Non-Goals

**Goals:**
- 采购入库详情为独立页面，内容完整。
- 已驳回的采购入库可编辑字段并重新提交进入审批。
- 领用出库支持一次添加多个物品。

**Non-Goals:**
- 不把采购聚合为单一订单（保持每物品一条 transfer）。
- 不改变审批/入库联动（上一变更已处理）。
- 不为调拨/回收/退还做同样改造（本变更只做采购详情页与领用多物品）。

## Decisions

### 决策 1：详情改独立页 + 路由
- **做法**：新增 `transfers/purchase/:id` 路由与 `PurchaseDetail.vue`；`PurchaseList` 详情按钮 `router.push` 到该页（移除弹窗）。详情页展示完整字段。
- **理由**：满足「第二界面」、信息完整、可承载编辑能力。

### 决策 2：驳回可编辑 + resubmit
- **做法**：详情页对「已驳回」记录显示编辑表单（**所有字段均可改**，含资产编号、分公司、数量、供应商、备注等），保存 = PATCH 更新字段；「重新提交」调后端 `resubmit`（已驳回→待审批）。
- 后端：新增 `resubmit` 动作（仅「已驳回」可调，→「待审批」）；`update`/`partial_update` 限制为仅「已驳回」可改（其他状态返回 400）。
- **理由**：驳回后修正重提是常见流程；限制 update 状态避免误改已通过/已入库记录。
- **备选**：允许任意状态编辑——有误改已入库风险，**否**。

### 决策 3：领用多行（参照 PurchaseCreateForm）
- **做法**：`AssignCreate.vue` 改多行：共享 调拨日期/分公司/备注，每行 资产编号/资产名称/数量/使用人；提交逐行 `assignAsset`（与采购逐行创建一致）。
- **理由**：与采购入库的多物品体验一致；复用既有 `assignAsset` 接口。

## Risks / Trade-offs

- **[update 权限收紧]** 现有 update 对认证用户开放 → **缓解**：本变更限制仅「已驳回」可改，更安全（不影响创建/审批）。
- **[多行部分失败]** 领用多行逐条创建，某行失败 → **缓解**：沿用采购提交的逐条模式，失败行报错、已成功行保留（与现状一致）。
- **[详情页与弹窗信息差]** 弹窗移除后信息全在详情页 → **缓解**：详情页展示完整字段 + 状态/审批信息。

## Migration Plan

1. 前端：新增 `PurchaseDetail.vue` + 路由；`PurchaseList` 详情跳转；`AssignCreate` 多行化。
2. 后端：`resubmit` 动作；`update` 限制「已驳回」。
3. 纯前后端逻辑，**无 DB 迁移**；部署即生效。

## Open Questions

（暂无。）

> 已定：已驳回编辑时**所有字段均可改**（含资产编号、分公司等）。
