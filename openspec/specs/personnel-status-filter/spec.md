# personnel-status-filter Specification

## Purpose
TBD - created by archiving change fix-organization-module. Update Purpose after archive.
## Requirements
### Requirement: 人员列表默认过滤已停用用户
人员管理标签页 SHALL 默认只显示 `status === 'active'` 的用户。用户可通过状态筛选下拉框切换查看全部或已停用用户。

#### Scenario: 默认只显示在职人员
- **WHEN** 用户打开人员管理标签页
- **THEN** 列表只显示 status 为 active 的人员

#### Scenario: 通过筛选查看已停用人员
- **WHEN** 用户在状态筛选中选择"已停用"
- **THEN** 列表显示 status 为 inactive 的人员

#### Scenario: 通过筛选查看全部人员
- **WHEN** 用户在状态筛选中选择"全部"
- **THEN** 列表显示所有人员（包括 active 和 inactive）

### Requirement: 删除按钮改为停用语义
人员管理中的"删除"操作 SHALL 在 UI 上改为"停用"语义。

#### Scenario: 按钮文案
- **WHEN** 用户查看在职人员的操作列
- **THEN** 显示"停用"按钮而非"删除"按钮

#### Scenario: 确认弹窗
- **WHEN** 用户点击"停用"按钮
- **THEN** 弹窗显示"确定停用该人员？停用后该人员将无法登录系统"

#### Scenario: 停用后列表刷新
- **WHEN** 用户确认停用某人员
- **THEN** 该人员从默认列表中消失（因为默认只显示 active 用户）

