# 调拨单调入方驳回通道 — 实施任务

## 1. 后端

- [x] 1.1 `transfers/models.py` 新增可空「调入方驳回原因」字段 + 迁移（纯加列，无 DML）
- [x] 1.2 `transfers/views.py` 新增 `inbound-reject` action：transfer 类型 + `validate_branches_in_scope(user, to_branch)` 反向断言 + 待审批限定 + 原因必填 + `select_for_update` 状态复查；类级 `required_operations` 补 `inbound_reject → manage_assets`
- [x] 1.3 `transfers/serializers.py` 新增 `canInboundReject` 输出（transfer && 待审批 && 范围含调入方 && canOperate 为 false）
- [x] 1.4 `notifications/signals.py`：待审批通知追加调入分公司持码收件人分支；驳回通知原因带【调入方驳回】前缀

## 2. 前端

- [x] 2.1 `api/transfers.ts` 新增 `inboundRejectTransfer`；`TransferList.vue` / `TransferDetailLayout.vue` 按 `canInboundReject` 显示「驳回」按钮（prompt 输原因）

## 3. 测试

- [x] 3.1 pytest：调入方驳回成功（状态+留痕+台账零变动）、阶段限定 400、调出方视角 400、无码 403、与 approve 并发竞争、通知收件人（调入方持码者收到、创建人收驳回通知）
- [x] 3.2 前端显隐用例 + 全量 `npm run test` + `npm run build`

## 4. 收口

- [ ] 4.1 手验清单：调入方收通知→驳回→调出方收通知→改单重提全链路；调出方审批无回归；本地验证后自行部署
- [x] 4.2 已知技术债记录：通知按姓名匹配创建人的重名漏发风险（独立处理，不混入本变更）
