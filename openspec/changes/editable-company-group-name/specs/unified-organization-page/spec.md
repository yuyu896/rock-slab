## ADDED Requirements

### Requirement: 集团名可编辑（Company 单例）

集团名 MUST 持久化在后端 `Company` 单例模型（预置「启航集团」），管理员 MUST 能在组织架构页编辑集团名（受 `manage_organizations`），改名 MUST 全局生效（所有用户看到新名）。组织树根节点 MUST 显示当前 `Company.name`。

#### Scenario: 编辑集团名

- **WHEN** 管理员在集团根点击「编辑集团」，输入新名并保存
- **THEN** 集团名更新为 `Company.name`，组织树根节点显示新名，所有用户生效

#### Scenario: 普通用户看到当前集团名

- **WHEN** 任意用户打开组织架构页
- **THEN** 根节点显示后端 `Company` 当前的 `name`
