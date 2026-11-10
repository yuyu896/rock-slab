## MODIFIED Requirements

### Requirement: Create personnel account

The system SHALL provide a "新增人员" button in the personnel management tab. Clicking it SHALL open a modal form with required fields: name, phone, role, and optional fields: branch（所属分公司）, team（所属行政组）, initial password. The default initial password SHALL be "123456".

**branch 与 team 互斥**：用户 MUST NOT 同时填写 branch 和 team；branch 有值时 team 置空，branch 为空时可单独填写 team 表示直接归属行政组。

#### Scenario: Create new personnel with branch

- **WHEN** user fills in name, phone, role, selects a branch, and clicks "确定保存"
- **THEN** the system SHALL send `POST /api/users/` with branch set and team null, show success message "创建成功", and refresh the list

#### Scenario: Create new personnel with team only (no branch)

- **WHEN** user fills in name, phone, role, selects a team but no branch, and clicks "确定保存"
- **THEN** the system SHALL send `POST /api/users/` with branch null and team set to the selected team id, show success message "创建成功"

#### Scenario: Create with missing required fields

- **WHEN** user submits the form without filling required fields
- **THEN** the system SHALL NOT submit and SHALL highlight the missing required fields

### Requirement: Edit personnel

The system SHALL provide an edit button in each row's action column. Clicking it SHALL open a modal pre-filled with the personnel's current data, including team（所属行政组）.

**branch 与 team 互斥**：编辑时 MUST 保持互斥约束，branch 有值则 team 只读显示派生值（`branch.teamName`），branch 为空时可编辑 team 字段。

#### Scenario: Edit personnel with branch shows team as readonly

- **WHEN** 员工有分公司归属，用户打开编辑弹窗
- **THEN** 所属行政组显示 `branch.teamName`，不可编辑

#### Scenario: Edit personnel without branch can set team

- **WHEN** 员工无分公司归属，用户打开编辑弹窗
- **THEN** 所属行政组字段可选，用户可修改 team 归属

#### Scenario: Edit personnel successfully

- **WHEN** user changes the name and clicks "确定保存"
- **THEN** the system SHALL send `PUT /api/users/<id>` with updated data, show success message "保存成功", and refresh the list
