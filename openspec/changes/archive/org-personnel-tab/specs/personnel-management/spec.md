## MODIFIED Requirements

### Requirement: Personnel list view
The system SHALL display a "人员管理" tab in the organization module. When selected, the system SHALL show a table listing all personnel with columns: name, phone, role, region, branch, leader, status, last login time, and actions. The system SHALL provide a search input and filter dropdowns (role, region, status) above the table.

#### Scenario: View personnel list
- **WHEN** user clicks the "人员管理" tab
- **THEN** the system SHALL display all users from the loaded `users` data in a table, sorted by creation time descending

#### Scenario: Empty personnel list
- **WHEN** no users exist in the system
- **THEN** the system SHALL display an empty state with message "暂无人员数据"

#### Scenario: Search by keyword
- **WHEN** user types a keyword in the search input
- **THEN** the system SHALL filter the table to show only users whose name or phone matches the keyword

#### Scenario: Filter by role
- **WHEN** user selects a role from the role dropdown
- **THEN** the system SHALL filter the table to show only users with that role

#### Scenario: Filter by status
- **WHEN** user selects a status from the status dropdown
- **THEN** the system SHALL filter the table to show only users with that status

#### Scenario: Combine search and filters
- **WHEN** user sets both search keyword and filter dropdowns
- **THEN** the system SHALL apply all conditions simultaneously
