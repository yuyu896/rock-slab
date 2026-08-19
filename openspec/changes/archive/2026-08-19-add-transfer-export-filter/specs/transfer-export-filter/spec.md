## ADDED Requirements

### Requirement: Transfer export with filter parameters
The system SHALL support exporting transfer records with filter parameters (branch, status, type) passed to the backend API, returning a complete filtered Excel file.

#### Scenario: Export with branch filter
- **WHEN** user selects a branch filter and clicks "导出" on any transfer type page
- **THEN** the system calls `exportTransfers` API with the selected branch parameter and downloads the filtered Excel file

#### Scenario: Export with status filter
- **WHEN** user selects a status filter and clicks "导出"
- **THEN** the exported Excel contains only records matching the selected status

#### Scenario: Export without filters
- **WHEN** user clicks "导出" without any filters applied
- **THEN** the system exports all records of the current transfer type

### Requirement: Purchase page export button
The Purchase.vue page SHALL have an export button in the header actions that downloads purchase transfer records as Excel.

#### Scenario: Export from purchase page
- **WHEN** user clicks "导出" on the Purchase.vue page
- **THEN** the system downloads an Excel file containing purchase type transfer records
