## ADDED Requirements

### Requirement: Dropdown trigger for parent menu items
The system SHALL render parent menu items (those with `children`) as dropdown triggers. Clicking a parent menu item SHALL toggle a floating dropdown panel anchored to the menu item, instead of expanding an inline sub-list.

#### Scenario: Open dropdown on click
- **WHEN** user clicks the "资产管理" menu item in the sidebar
- **THEN** a floating dropdown panel appears anchored to the right side of the menu item, displaying all child items (资产列表, 采购入库, 调拨记录)

#### Scenario: Close dropdown on second click
- **WHEN** user clicks the "资产管理" menu item while the dropdown is already open
- **THEN** the dropdown panel closes

#### Scenario: Close dropdown on outside click
- **WHEN** user clicks anywhere outside the dropdown panel and the parent menu item
- **THEN** the dropdown panel closes

### Requirement: Dropdown navigation
The system SHALL allow direct navigation from dropdown items. Clicking a dropdown child item SHALL navigate to the corresponding route and close the dropdown.

#### Scenario: Navigate to child route
- **WHEN** user clicks "资产列表" in the dropdown
- **THEN** system navigates to `/assets/list` and the dropdown closes

#### Scenario: Active route highlighting
- **WHEN** current route matches a child item path (e.g., `/assets/list`)
- **THEN** both the parent menu item and the matching child item in the dropdown SHALL display active styling

### Requirement: Collapsed sidebar dropdown support
The system SHALL support the dropdown when the sidebar is collapsed. When collapsed, clicking the parent icon SHALL open the dropdown anchored to the right of the icon, with a fixed width sufficient to display item labels.

#### Scenario: Collapsed sidebar dropdown
- **WHEN** sidebar is collapsed and user clicks the "资产管理" icon
- **THEN** a dropdown appears anchored to the right side of the icon with full-width item labels

### Requirement: Dropdown animation
The system SHALL provide a smooth transition animation when the dropdown opens and closes.

#### Scenario: Open animation
- **WHEN** dropdown opens
- **THEN** the dropdown fades in or slides in with a short transition (under 200ms)

#### Scenario: Close animation
- **WHEN** dropdown closes
- **THEN** the dropdown fades out or slides out with a short transition (under 200ms)
