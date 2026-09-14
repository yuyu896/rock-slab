# transfer-line-items 增量

## ADDED Requirements

### Requirement: 单据分公司语义化构造

Transfer 单据的分公司装载 MUST 收口于模型语义化构造器 `Transfer.build`：采购/领用/归还/回收经 `所属分公司`（采购落 to_branch 其余落 from_branch，另一侧恒空）、调拨经 `调出分公司`+`调入分公司`——类型到字段的映射唯一存在于模型内。业务代码（视图/导入/服务）MUST NOT 直接对 `from_branch=`/`to_branch=` 赋值（架构测试执法，白名单：模型自身/migrations/tests）。模型 SHALL 提供类型化读取属性 `业务分公司`（采购→to_branch，其余→from_branch）。

#### Scenario: 采购经构造器落库方向正确

- **WHEN** `Transfer.build(action_type='purchase', 所属分公司=B, ...)` 创建采购单
- **THEN** to_branch=B、from_branch 为空——方向由构造器保证，调用方无从装反

#### Scenario: 调拨收两侧

- **WHEN** 调拨经 `Transfer.build(调出分公司=A, 调入分公司=B, ...)`
- **THEN** from_branch=A、to_branch=B

#### Scenario: 架构测试抓直赋

- **WHEN** 某视图代码出现 `Transfer(from_branch=...)` 或 `.from_branch =`
- **THEN** 架构测试失败并指出违规文件
