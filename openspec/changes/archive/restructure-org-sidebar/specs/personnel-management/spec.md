## MODIFIED Requirements

### Requirement: Personnel list view
The system SHALL display a "人员管理" tab in the organization module. When selected, the system SHALL show a table listing all personnel with columns: name, phone, role, region, branch, team, leader, status, last login time, and actions.

#### Scenario: View personnel list
- **WHEN** user clicks the "人员管理" tab
- **THEN** the system SHALL fetch all users via `GET /api/users/` and display them in a table sorted by creation time descending, including the team column

#### Scenario: Empty personnel list
- **WHEN** no users exist in the system
- **THEN** the system SHALL display an empty state with message "暂无人员数据"

### Requirement: Personnel filter
The system SHALL provide dropdown filters above the table for: role, region, branch, team, and status. Filters SHALL be combinable.

#### Scenario: Filter by role
- **WHEN** user selects a role from the role dropdown
- **THEN** the system SHALL send `GET /api/users/?role=<role>` and display matching results

#### Scenario: Filter by branch
- **WHEN** user selects a branch from the branch dropdown
- **THEN** the system SHALL send `GET /api/users/?branch=<branchId>` and display matching results

#### Scenario: Filter by team
- **WHEN** user selects a team from the team dropdown
- **THEN** the system SHALL send `GET /api/users/?team=<teamId>` and display matching results

#### Scenario: Combine multiple filters
- **WHEN** user sets both role and region filters
- **THEN** the system SHALL send `GET /api/users/?role=<role>&region=<regionId>` with all selected filters

## ADDED Requirements

### Requirement: Organization sidebar hierarchy
The organization module sidebar SHALL display a hierarchical tree with fixed structure: 集团 (root) → 行政经理 + 区域 → 行政主管 + 行政组 → 行政组长 + 组员. The tree SHALL NOT use the User `leader` self-reference for hierarchy; instead it SHALL use Region→Team→User relationships.

#### Scenario: View full hierarchy
- **WHEN** user opens the organization module
- **THEN** the sidebar SHALL show "集团" as the fixed root node, with manager users and regions as children, supervisors and teams under each region, and leader+staff under each team

#### Scenario: Select person in tree
- **WHEN** user clicks a person node in the tree
- **THEN** the right panel SHALL display that person's detail information including their team, region, and role

#### Scenario: Select team in tree
- **WHEN** user clicks a team node in the tree
- **THEN** the right panel SHALL display team details: name, region, leader, member count, and member list

### Requirement: Create personnel with team
The system SHALL include a team selection field in the create personnel form. When creating a user with role `leader` or `staff`, the team field SHALL be available.

#### Scenario: Create personnel with team assignment
- **WHEN** user fills in name, phone, role "staff", selects a region and team, and clicks "确定保存"
- **THEN** the system SHALL create the user with the selected team association and refresh the sidebar tree

#### Scenario: Team dropdown filtered by region
- **WHEN** user selects a region in the create form
- **THEN** the team dropdown SHALL only show teams belonging to the selected region
