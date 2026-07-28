## ADDED Requirements

### Requirement: 通知收件人必须按数据范围授权收敛

审批与抄送通知 MUST 仅发送给对源单据所属分公司（`调出分公司` / 任务 `branch`）持有数据范围授权的用户，即 `resolve_user_scope(recipient).branches` 包含该分公司的用户。不得按角色全量广播，也不得向无权查看该业务数据的用户推送含资产名称 / 编号 / 调出调入分公司的通知明细。

#### Scenario: 跨区域调拨不通知无关区域审批人
- **WHEN** 区域 A 发起一笔调拨，其 `调出分公司` 属于区域 A
- **THEN** 仅授权范围含区域 A 该分公司的用户收到待审批通知；区域 B 的 manager（对该分公司无授权）不收到通知

#### Scenario: director 按授权范围收到通知
- **WHEN** 一笔单据进入待审批，且某 `director` 的 `ManagementScope` 授权包含该分公司
- **THEN** 该 director 收到通知；授权范围不含该分公司的 director 不收到
