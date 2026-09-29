# 调拨单调入方驳回通道 — 技术设计

## Context

调拨单边发起（修订 3.1）：调出方创建+审批即向调入方注入库存，调入方只读无通知。调研事实：①「已通过」在 approve 同事务内写台账（[transfers/views.py:301](../../../backend/apps/transfers/views.py) → [ledger.py:209-333](../../../backend/apps/assets/services/ledger.py)），**无未生效窗口**，已生效禁删；②现有 approve 被「approve_transfer 码 + 调出方断言」双闸把调入方拦死；③驳回→改单→resubmit 链路完整（views.py:327-338）；④通知现状只发调出方（[signals.py:76-116](../../../backend/apps/notifications/signals.py)）；⑤并发防护模式 select_for_update+状态复查现成（views.py:289-294）。

## Goals / Non-Goals

**Goals:** 调入方在「待审批」阶段有通知、能驳回；驳回零台账影响；与调出方审批并发安全。

**Non-Goals:** 不提供已生效单据的逆向通道（拒收走既有台账调整单）；不动调拨单边创建/审批口径；不引入新操作码。

## Decisions

### D1：驳回窗口仅「待审批」

唯一零台账影响的窗口；草稿调出方自己可撤、已通过已生效只能走调整单。状态转「已驳回」，复用既有驳回语义（创建人收通知、可改单 resubmit 重提、调入方可再驳——业务自平衡）。

### D2：新 action `inbound-reject` + 反向断言，复用 `manage_assets` 码

不复用 approve（双闸拦调入方且语义混淆）。新 action 断言：transfer 类型 + `validate_branches_in_scope(user, to_branch)`（反向：范围须含**调入**分公司）+ 状态待审批 + 原因必填；类级 `required_operations` 补 `'inbound_reject': 'manage_assets'`。
复用 manage_assets 理由：调入方分公司行政（manager）/组长（leader）模板已含——"管理本公司被调入资产"语义贴切；与 authz-hardening-2 盘点挂码同一取舍（不加码不动模板/种子/门禁）。备选新码 `reject_inbound_transfer`：四处联动成本高，弃（后续需要更细口径再演进）。

### D3：审计分列——新增可空「调入方驳回原因」字段

`Transfer.调入方驳回原因`（CharField 可空）+ 一次小迁移；「审批人」照写驳回操作者。与调出方审批驳回（既有驳回原因字段）分列留痕，审计可辨双方动作；serializer 输出该字段供前端展示。

### D4：通知——待审批时增加调入方分支

`notify_transfer_created`（signals.py:76-116）追加：transfer 类型时，收件人并集**调入分公司范围内持 manage_assets 者**（复用现有按范围找人的 helper）；驳回动作复用既有「待审批→已驳回」通知创建人分支（signals.py:201-221），原因带【调入方驳回】前缀以示来源。

### D5：前端——`canInboundReject` 序列化 + 按钮显隐

serializers 的 canOperate 旁新增 `canInboundReject`（后端算好：transfer 类型 && 待审批 && 范围含调入方 && 非可操作视角）；列表行与详情 footer 在 `canOperate==false && canInboundReject` 时显示「驳回」（prompt 输原因，走新 API）。前端不算权限，展示完全由后端口径下发。

## Risks / Trade-offs

- [调出方审批与调入方驳回并发] → select_for_update + 状态复查照搬 approve 模式，后到者 400。
- [驳回-重提拉锯] → 业务自平衡，不设次数限制；通知保证双方知情。
- [通知按姓名匹配创建人（重名漏发，既有问题）] → 本变更不扩面修，记录为独立技术债。
- [manage_assets 语义外延（驳回权随管理码走）] → 与盘点挂码同口径；若未来要求仅行政可驳，届时升专码。

## Migration Plan

后端含一次无 DML 的加列迁移（安全）；随常规发版。上线后验证：调入方收到待审批通知、可驳回、驳回后调出方收到通知且可改单重提；调出方审批流程无回归。

## Open Questions

（无——「仅待审批阶段」「复用 manage_assets」「审计分列」三个口径均已按拍板方向（单边+驳回通道）推导定案，提案阶段可驳。）
