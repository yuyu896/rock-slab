## REMOVED Requirements

### Requirement: 领用出库审批后扣减库存
**Reason**: 扣减基准从「资产编号+分公司匹配的 Asset 数量」改为台账在库列，且新增在库充足性行锁校验；旧契约的「状态改为使用中/已领完」语义随 Asset 冻结废止。
**Migration**: 领用台账联动与充足性校验契约见 `document-ledger-sync` 能力。

### Requirement: 调拨审批后调出降调入增
**Reason**: 双边变动基准从 Asset 数量改为台账在库列（调入无行则建行语义保留），并新增调出充足性校验。
**Migration**: 调拨台账联动契约见 `document-ledger-sync` 能力。
