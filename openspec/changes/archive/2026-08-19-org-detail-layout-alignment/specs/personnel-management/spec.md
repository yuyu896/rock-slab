## MODIFIED Requirements

### Requirement: Personnel list view

The system SHALL display a "人员管理" tab in the organization module. When selected, the system SHALL show a table listing all personnel with columns: name, phone, role, region, branch, leader, status, last login time, and actions.

人员详情头部区域 SHALL 满足以下布局要求：
- 编辑、删除按钮 SHALL 在详情头部区域垂直居中显示
- 角色标签（如"行政经理"）SHALL 与人员姓名左对齐

#### Scenario: View personnel list
- **WHEN** user clicks the "人员管理" tab
- **THEN** the system SHALL fetch all users via `GET /api/users/` and display them in a table sorted by creation time descending

#### Scenario: Empty personnel list
- **WHEN** no users exist in the system
- **THEN** the system SHALL display an empty state with message "暂无人员数据"

#### Scenario: Detail header actions are vertically centered
- **WHEN** 用户查看人员详情头部
- **THEN** 编辑和删除按钮 SHALL 在头部区域垂直居中，而非贴顶部

#### Scenario: Role label aligns with name
- **WHEN** 用户查看人员详情头部
- **THEN** 角色标签文字 SHALL 与姓名文字左对齐
