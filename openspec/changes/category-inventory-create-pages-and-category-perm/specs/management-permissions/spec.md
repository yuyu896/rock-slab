# 管理权限授权模型（management-permissions delta）

品目写操作的前端入口按 `manage_categories` 操作授权控制可见性。

## MODIFIED Requirements

### Requirement: 系统必须支持按业务操作授予管理权限

系统 MUST 提供业务操作维度的授权，可为员工授予具体的业务操作权限（如审批采购、管理用户、管理品目）；接口级权限 MUST 基于员工是否持有对应操作授权来判断，而非职位等级。**前端写操作入口 MUST 按对应操作授权控制可见性**——持有授权或 admin 才显示写入口，无授权用户仅见只读视图。

#### Scenario: 持有操作授权方可执行

- **WHEN** 员工 C 被授予 `approve_transfer` 操作授权
- **THEN** C 调用资产调拨审批接口时 MUST 被放行
- **AND** 未被授予该操作的员工 D（非 admin）调用同一接口 MUST 被拒绝（403）

#### Scenario: 接口权限不再依赖职位等级

- **WHEN** 一位 `staff` 职位的员工被授予某业务操作授权
- **THEN** 该员工执行该操作时 MUST 被放行
- **AND** 系统 MUST NOT 因其职位等级为 staff 而拒绝

#### Scenario: 品目写入口按授权可见

- **WHEN** 一个未持有 `manage_categories` 授权的非 admin 用户访问品目模块
- **THEN** 品目列表页 MUST NOT 显示新增 / 编辑 / 删除 / 导入入口
- **AND** 该用户 MUST 仅能查看品目列表（只读）
- **AND** 持有 `manage_categories` 授权或 admin 用户 MUST 能看到并使用这些写入口
