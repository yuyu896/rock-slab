# personnel-management Specification

## Purpose
TBD - created by archiving change add-personnel-management. Update Purpose after archive.
## Requirements
### Requirement: Personnel list view
The system SHALL display a "人员管理" tab in the organization module. When selected, the system SHALL show a table listing all personnel with columns: name, phone, role, region, branch, leader, status, last login time, and actions.

#### Scenario: View personnel list
- **WHEN** user clicks the "人员管理" tab
- **THEN** the system SHALL fetch all users via `GET /api/users/` and display them in a table sorted by creation time descending

#### Scenario: Empty personnel list
- **WHEN** no users exist in the system
- **THEN** the system SHALL display an empty state with message "暂无人员数据"

### Requirement: Personnel search
The system SHALL provide a search input above the personnel table. The system SHALL filter personnel by name or phone number matching the keyword.

#### Scenario: Search by name
- **WHEN** user types a keyword in the search input
- **THEN** the system SHALL send `GET /api/users/?keyword=<keyword>` and display matching results

#### Scenario: Clear search
- **WHEN** user clears the search input
- **THEN** the system SHALL reload the full personnel list

### Requirement: Personnel filter
The system SHALL provide dropdown filters above the table for: role, region, branch, and status. Filters SHALL be combinable.

#### Scenario: Filter by role
- **WHEN** user selects a role from the role dropdown
- **THEN** the system SHALL send `GET /api/users/?role=<role>` and display matching results

#### Scenario: Filter by branch
- **WHEN** user selects a branch from the branch dropdown
- **THEN** the system SHALL send `GET /api/users/?branch=<branchId>` and display matching results

#### Scenario: Combine multiple filters
- **WHEN** user sets both role and region filters
- **THEN** the system SHALL send `GET /api/users/?role=<role>&region=<regionId>` with all selected filters

### Requirement: Create personnel account
The system SHALL provide a "新增人员" button in the personnel management tab. Clicking it SHALL open a modal form with required fields: name, phone, role, region, and optional fields: branch, leader, initial password. The default initial password SHALL be "123456".

#### Scenario: Create new personnel successfully
- **WHEN** user fills in name "张三", phone "13800138000", role "staff", selects a region, and clicks "确定保存"
- **THEN** the system SHALL send `POST /api/users/` with the form data and password, show success message "创建成功", and refresh the list

#### Scenario: Create with missing required fields
- **WHEN** user submits the form without filling required fields
- **THEN** the system SHALL NOT submit and SHALL highlight the missing required fields

### Requirement: Edit personnel
The system SHALL provide an edit button in each row's action column. Clicking it SHALL open a modal pre-filled with the personnel's current data.

#### Scenario: Edit personnel successfully
- **WHEN** user changes the name from "张三" to "李四" and clicks "确定保存"
- **THEN** the system SHALL send `PUT /api/users/<id>` with updated data, show success message "保存成功", and refresh the list

### Requirement: Toggle personnel status
The system SHALL provide a status toggle switch in each row. Toggling SHALL switch between active and inactive status.

#### Scenario: Disable an active account
- **WHEN** user toggles off an active account
- **THEN** the system SHALL send `PUT /api/users/<id>` with `status: "inactive"`, show message "已停用", and update the table

#### Scenario: Enable an inactive account
- **WHEN** user toggles on an inactive account
- **THEN** the system SHALL send `PUT /api/users/<id>` with `status: "active"`, show message "已启用", and update the table

### Requirement: Delete personnel
The system SHALL provide a delete button in each row's action column. Clicking it SHALL show a confirmation dialog before deletion.

#### Scenario: Delete personnel successfully
- **WHEN** user clicks delete on a row and confirms the dialog
- **THEN** the system SHALL send `DELETE /api/users/<id>`, show success message "删除成功", and refresh the list

#### Scenario: Cancel deletion
- **WHEN** user clicks delete on a row but cancels the confirmation dialog
- **THEN** the system SHALL NOT send any request and the list SHALL remain unchanged

