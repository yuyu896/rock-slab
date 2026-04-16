## ADDED Requirements

### Requirement: Asset 模型分公司字段改为 FK
`Asset` 模型 SHALL 包含一个指向 `Branch` 模型的 FK 字段 `branch`，用于关联资产所属分公司。

#### Scenario: 创建资产时关联分公司
- **WHEN** 通过采购入库创建新资产
- **THEN** 系统 SHALL 将资产关联到对应的 Branch 记录，`branch_id` MUST 非 null

#### Scenario: 按分公司筛选资产使用 FK 查询
- **WHEN** 前端请求资产列表并按分公司筛选
- **THEN** 系统 SHALL 通过 FK 关系查询，而非字符串匹配

### Requirement: Transfer 模型分公司字段改为 FK
`Transfer` 模型 SHALL 包含 `from_branch` 和 `to_branch` 两个 FK 字段，分别指向 `Branch` 模型，替代现有的字符串分公司字段。

#### Scenario: 调拨单关联源和目标分公司
- **WHEN** 创建资产调拨单
- **THEN** 系统 SHALL 通过 FK 记录调出和调入分公司

#### Scenario: 分公司更名后数据一致
- **WHEN** Branch 记录的名称被修改
- **THEN** 关联的 Asset 和 Transfer 记录 SHALL 自动反映新名称，无需手动同步

### Requirement: 现有数据迁移
系统 SHALL 提供数据迁移脚本，将现有 Asset 和 Transfer 中以字符串存储的分公司名称匹配到对应的 Branch 记录，并填充 FK 字段。

#### Scenario: 字符串数据成功匹配
- **WHEN** 迁移脚本执行时，某资产的 `分公司` 字段值为 "上海分公司"，且 Branch 表中存在该名称
- **THEN** 脚本 SHALL 将该资产的 `branch_id` 设置为对应 Branch 的 ID

#### Scenario: 字符串数据无法匹配
- **WHEN** 迁移脚本执行时，某资产的 `分公司` 字段值在 Branch 表中无匹配记录
- **THEN** 脚本 SHALL 输出未匹配记录的报告（ID 和分公司名称），不中断迁移流程
