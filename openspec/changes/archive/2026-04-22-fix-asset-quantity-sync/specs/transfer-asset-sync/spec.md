## ADDED Requirements

### Requirement: 领用审批通过后更新 Asset 状态
领用(assign)操作审批通过后，系统 SHALL 将对应 Asset 的 `当前状态` 从"在库"改为"使用中"。

#### Scenario: 领用单审批通过
- **WHEN** 领用类型的 Transfer 审批状态从"待审批"变为"已通过"
- **THEN** 对应 `资产编号` 的 Asset `当前状态` 更新为"使用中"

#### Scenario: 领用的 Asset 不存在
- **WHEN** 领用单审批通过但对应的 `资产编号` 在 Asset 表中不存在
- **THEN** 审批仍然成功，不报错

### Requirement: 归还审批通过后更新 Asset 状态
归还(return)操作审批通过后，系统 SHALL 将对应 Asset 的 `当前状态` 改回"在库"。

#### Scenario: 归还单审批通过
- **WHEN** 归还类型的 Transfer 审批状态从"待审批"变为"已通过"
- **THEN** 对应 `资产编号` 的 Asset `当前状态` 更新为"在库"

### Requirement: 调拨审批通过后更新 Asset 归属
调拨(transfer)操作审批通过后，系统 SHALL 将对应 Asset 的分公司、区域字段更新为目标分公司。

#### Scenario: 调拨单审批通过
- **WHEN** 调拨类型的 Transfer 审批状态从"待审批"变为"已通过"
- **THEN** 对应 `资产编号` 的 Asset 的分公司字段更新为 Transfer 的目标分公司
