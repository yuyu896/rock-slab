## ADDED Requirements

### Requirement: Sidebar inventory badge shows dynamic count
The system SHALL display a badge next to the "资产盘点" menu item in the sidebar that reflects the current count of inventory tasks with status `pending` or `in_progress`.

#### Scenario: Active inventory tasks exist
- **WHEN** there are inventory tasks with status `pending` or `in_progress`
- **THEN** the sidebar "资产盘点" menu item SHALL display a red badge showing the total count of such tasks

#### Scenario: No active inventory tasks
- **WHEN** there are zero inventory tasks with status `pending` or `in_progress`
- **THEN** the sidebar "资产盘点" menu item SHALL NOT display any badge

### Requirement: Badge count fetched on component mount
The system SHALL fetch the badge count by calling `getInventoryTasks` with `status: 'pending,in_progress'` and `pageSize: 1` when the SidebarNav component is mounted, using only the `count` field from the API response.

#### Scenario: Component loads and API succeeds
- **WHEN** SidebarNav component mounts and the API call succeeds
- **THEN** the badge SHALL display the `count` value from the response

#### Scenario: Component loads and API fails
- **WHEN** SidebarNav component mounts and the API call fails
- **THEN** no badge SHALL be displayed (count defaults to 0)
