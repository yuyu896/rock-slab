## ADDED Requirements

### Requirement: Transfer 操作审计记录
系统 SHALL 对所有资产流转操作（采购、领用、归还、调拨、维修、报废、审批）记录审计日志。

#### Scenario: 采购入库操作审计
- **WHEN** 用户通过 POST `/api/transfers/purchase` 创建采购入库单
- **THEN** 系统 SHALL 创建一条审计日志，包含操作人、操作类型、操作时间和变更前后数据快照

#### Scenario: 审批操作审计
- **WHEN** 行政主管通过 POST `/api/transfers/:id/approve` 审批单据
- **THEN** 系统 SHALL 记录审批操作，包含审批结果和审批人信息

### Requirement: Inventory 操作审计记录
系统 SHALL 对盘点任务的关键状态变更操作（开始、提交、审批、驳回、取消）记录审计日志。

#### Scenario: 开始盘点审计
- **WHEN** 用户通过 POST `/api/inventories/:id/start` 开始盘点
- **THEN** 系统 SHALL 记录盘点开始操作和操作人

#### Scenario: 盘点审批审计
- **WHEN** 行政主管审批盘点结果
- **THEN** 系统 SHALL 记录审批操作和审批结果

### Requirement: 用户管理操作审计记录
系统 SHALL 对用户创建、更新、停用操作记录审计日志。

#### Scenario: 创建用户审计
- **WHEN** 管理员通过 POST `/api/users/` 创建新用户
- **THEN** 系统 SHALL 记录新用户的关键信息（不含密码）

#### Scenario: 停用用户审计
- **WHEN** 管理员停用某用户
- **THEN** 系统 SHALL 记录被停用用户的 ID 和操作人
