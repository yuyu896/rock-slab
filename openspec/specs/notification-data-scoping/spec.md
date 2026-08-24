# notification-data-scoping Specification

## Purpose
TBD - created by archiving change audit-findings-remediation. Update Purpose after archive.
## Requirements
### Requirement: 通知收件人必须按数据范围授权收敛

审批与抄送通知 MUST 仅发送给对源单据所属分公司（`调出分公司` / 任务 `branch`）持有数据范围授权的用户，即 `resolve_user_scope(recipient).branches` 包含该分公司的用户。不得按角色全量广播，也不得向无权查看该业务数据的用户推送含资产名称 / 编号 / 调出调入分公司的通知明细。

#### Scenario: 跨区域调拨不通知无关区域审批人
- **WHEN** 区域 A 发起一笔调拨，其 `调出分公司` 属于区域 A
- **THEN** 仅授权范围含区域 A 该分公司的用户收到待审批通知；区域 B 的 manager（对该分公司无授权）不收到通知

#### Scenario: director 按授权范围收到通知
- **WHEN** 一笔单据进入待审批，且某 `director` 的 `ManagementScope` 授权包含该分公司
- **THEN** 该 director 收到通知；授权范围不含该分公司的 director 不收到


### Requirement: 多明细单据通知摘要
流转单触发的通知 MUST 以明细摘要描述单据：首行品目名称 +（行数大于 1 时）"等 N 项"、数量为各行合计；收件人收敛规则（按数据范围授权）保持既有契约不变。

#### Scenario: 多行单据通知显示摘要
- **WHEN** 一张含 品目 X×2、品目 Y×3 的领用单进入待审批
- **THEN** 通知文本形如「品目 X 等 2 项（共 5 件）」，不逐行罗列全部明细
