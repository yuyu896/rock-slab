# 调拨单调入方驳回通道（transfer-inbound-reject）

## Why

调拨按修订 3.1 单边发起：调出方创建并审批即可向**任意**调入分公司注入库存，调入方对单据只读、**无拒绝通道**、全程无通知——缺陷清单中危项，用户拍板走「维持单边发起 + 调入方驳回通道」而非双边校验（保住跨范围调拨能力，堵住单边注入）。

调研结论（2026-09-29）：调拨「已通过」即同事务写台账生效，**不存在未生效窗口**——故驳回通道限定在**待审批阶段**（此阶段驳回零台账影响）；已生效单据只能走既有台账调整单，不提供逆向通道。

## What Changes

- **新动作 `inbound-reject`**（transfer 类型专用）：数据范围含**调入分公司**的用户可对待审批调拨单发起驳回 → 单据转「已驳回」，须填原因；沿用 `select_for_update` 并发防护，与调出方审批竞争安全。
- **权限**：复用 `manage_assets` 操作码（调入方分公司行政/组长模板已含，不新增码、不动模板/种子/门禁）。
- **审计区分**：`Transfer` 新增可空「调入方驳回原因」字段（与调出方审批驳回分列留痕，审批人字段照写操作者）；一次小迁移。
- **调入方通知**：调拨单进入待审批时，通知调入分公司范围内持 `manage_assets` 者（现通知只发调出方）；驳回后通知创建人（复用既有驳回通知分支）。
- **前端**：调拨单列表/详情对「数据范围含调入方 && 待审批 && canOperate==false」的调入方视角显示「驳回」按钮；通知点击跳转列表（现状）不动。
- 驳回后创建人可改单 resubmit 重提（既有链路），调入方可再驳——业务自平衡。

## Capabilities

### New Capabilities

- `transfer-inbound-reject`：调拨单调入方在待审批阶段的可见性、通知与驳回通道。

### Modified Capabilities

（无——调拨单边创建/审批口径不变；`write-authorization-scoping` 的调拨例外表述不受影响。）

## Impact

- `backend/apps/transfers/views.py`（新 action + 反向断言）、`models.py`（字段 + 迁移）、`notifications/signals.py`（调入方通知分支）、`transfers/serializers.py`（canInboundReject 序列化）。
- `frontend/src/api/transfers.ts`、`TransferList.vue`/`TransferDetailLayout.vue`（驳回按钮）、`useTransferList.ts`。
- 测试：驳回成功/阶段限定（草稿·已通过不可驳）/并发竞争/通知收件人/前端按钮显隐。提案审查两问：驳回发生在生效前、无台账数量变动（写台账仍只经 approve 链路），通过。
