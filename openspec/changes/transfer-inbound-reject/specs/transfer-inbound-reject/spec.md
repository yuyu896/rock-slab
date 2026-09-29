# transfer-inbound-reject Delta

## ADDED Requirements

### Requirement: 调入方待审批阶段驳回通道
transfer 类型单据处于「待审批」阶段时，数据范围含**调入分公司**且持 `manage_assets` 操作码的用户（含 admin）SHALL 可通过 `inbound-reject` 动作驳回该单据：原因必填，驳回后单据转「已驳回」（创建人可改单重提），全程不触碰台账。驳回 SHALL 与调出方审批并发安全（行锁+状态复查，后到者失败）。非 transfer 类型、非待审批阶段（草稿/已通过/已入库/已驳回）、范围不含调入分公司、或无操作码的请求 SHALL 被拒。

#### Scenario: 调入方驳回待审批调拨
- **WHEN** 数据范围含调入分公司的持码用户对待审批的 transfer 单据发起 `inbound-reject`（附原因）
- **THEN** 单据转「已驳回」，驳回原因与操作者留痕，台账无任何变动

#### Scenario: 阶段限定
- **WHEN** 对草稿、已通过、已入库或已驳回的 transfer 单据发起 `inbound-reject`
- **THEN** 系统返回 400，单据状态不变

#### Scenario: 调出方视角不可用
- **WHEN** 数据范围仅含调出分公司的用户（调出方操作者）发起 `inbound-reject`
- **THEN** 系统返回 400（驳回通道属调入方），其既有审批/编辑路径不受影响

#### Scenario: 无码用户被拒
- **WHEN** 数据范围含调入分公司但无 `manage_assets` 的用户发起 `inbound-reject`
- **THEN** 系统返回 403

#### Scenario: 与审批并发安全
- **WHEN** 调出方审批与调入方驳回同时到达
- **THEN** 先到者生效，后到者因状态已变返回 400，单据状态与台账保持一致

#### Scenario: 驳回后重提闭环
- **WHEN** 被调入方驳回的单据由创建人修改后 resubmit
- **THEN** 单据回到待审批，调入方可再次驳回（不设次数限制）

#### Scenario: 审计留痕分列
- **WHEN** 调入方驳回发生后查看单据
- **THEN** 驳回原因记录于「调入方驳回原因」字段并可区分于调出方审批驳回，操作者记于审批人字段

### Requirement: 调入方待审批通知
transfer 类型单据进入「待审批」时，系统 SHALL 通知**调入分公司**范围内持 `manage_assets` 的用户（与调出方审批人通知并行发出）；调入方驳回后 SHALL 复用既有驳回通知通道通知创建人，原因带【调入方驳回】标识。

#### Scenario: 调入方收到待审批提醒
- **WHEN** 调出方提交一笔调入分公司为 B 的调拨进入待审批
- **THEN** B 分公司范围内持 manage_assets 的用户收到该单据的通知

#### Scenario: 驳回通知创建人
- **WHEN** 调入方驳回该调拨
- **THEN** 单据创建人收到驳回通知，原因可见「调入方驳回」来源标识
