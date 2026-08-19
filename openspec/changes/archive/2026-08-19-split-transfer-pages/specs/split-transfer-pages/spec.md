## ADDED Requirements

### Requirement: Sidebar navigation for transfer types
The system SHALL display a "资产流转" sub-group under the "资产管理" sidebar section, with expandable child menu items for each transfer type: 采购入库、领用出库、归还、调拨、维修、报废.

#### Scenario: Sidebar shows transfer sub-menu
- **WHEN** user expands the "资产管理" section in the sidebar
- **THEN** the system displays "资产流转" as a sub-group with 6 child items: 采购入库、领用出库、归还、调拨、维修、报废

#### Scenario: Active transfer type is highlighted in sidebar
- **WHEN** user navigates to any transfer type page (e.g., /transfers/assign)
- **THEN** the corresponding sidebar menu item is visually highlighted as active

### Requirement: Independent route per transfer type
The system SHALL provide a unique route for each transfer type: `/transfers/purchase`, `/transfers/assign`, `/transfers/return`, `/transfers/transfer`, `/transfers/repair`, `/transfers/scrap`.

#### Scenario: Direct URL access to transfer type page
- **WHEN** user navigates to `/transfers/repair`
- **THEN** the system displays the repair transfer list page filtered to repair type only

#### Scenario: Legacy route redirects to new route
- **WHEN** user navigates to the old route `/assets/transfer`
- **THEN** the system redirects to `/transfers/transfer`

### Requirement: Independent page per transfer type
Each transfer type SHALL have its own Vue page component with an independent list view, filters, create form, detail modal, and approval actions, scoped to that single transfer type.

#### Scenario: Transfer type page shows filtered list
- **WHEN** user opens the "领用出库" page
- **THEN** the list shows only assign-type transfers, fetched via `getTransfers({ type: 'assign' })`

#### Scenario: Transfer type page has type-specific create form
- **WHEN** user clicks "新建" on the "调拨" page
- **THEN** the create modal shows only the fields relevant to transfer type (调出/调入分公司、部门、负责人、调拨原因)

#### Scenario: Transfer type page has type-specific create form for repair
- **WHEN** user clicks "新建" on the "维修" page
- **THEN** the create modal shows repair-specific fields (维修原因) without irrelevant fields

### Requirement: Shared transfer list composable
The system SHALL provide a `useTransferList` composable function that encapsulates common data fetching, pagination, filtering, approval, detail viewing, and export logic shared across all 6 transfer type pages.

#### Scenario: Composable provides type-scoped data
- **WHEN** a page component calls `useTransferList('repair')`
- **THEN** the composable returns reactive transfers list, pagination, filters, and methods scoped to repair type

#### Scenario: Composable handles approval actions
- **WHEN** user approves or rejects a transfer on any type page
- **THEN** the composable calls the appropriate API and refreshes the list

### Requirement: Transfer type pages support batch import
Each transfer type page SHALL support the existing batch import functionality (download template, upload Excel, view results).

#### Scenario: Batch import on transfer type page
- **WHEN** user clicks "批量导入" on any transfer type page
- **THEN** the import modal opens with the same download template / upload file / view results workflow
