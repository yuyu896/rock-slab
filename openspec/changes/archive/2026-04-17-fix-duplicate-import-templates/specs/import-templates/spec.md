## MODIFIED Requirements

### Requirement: Import template differentiated by business type
The system SHALL generate distinct import templates for each business page. Each template SHALL have a unique file name and pre-filled "流转类型" column matching the page's business type.

#### Scenario: Download template from purchase page
- **WHEN** user clicks "下载模板" in the purchase import dialog
- **THEN** system downloads "采购入库导入模板.xlsx" with the "流转类型" column pre-filled as "采购入库"

#### Scenario: Download template from assign page
- **WHEN** user clicks "下载模板" in the assign list import dialog
- **THEN** system downloads "领用出库导入模板.xlsx" with the "流转类型" column pre-filled as "领用出库"

#### Scenario: Download template from transfer page
- **WHEN** user clicks "下载模板" in the transfer list import dialog
- **THEN** system downloads "调拨导入模板.xlsx" with the "流转类型" column pre-filled as "调拨"

### Requirement: Purchase page import uses transfer flow
The purchase page import dialog SHALL import data through the transfer import API (`/api/transfers/import`), NOT the asset import API. The dialog SHALL use the purchase-specific transfer template (14-column format with "流转类型" pre-filled as "采购入库").

#### Scenario: Import file from purchase page
- **WHEN** user uploads an Excel file in the purchase import dialog
- **THEN** system calls `/api/transfers/import` to import the data as purchase transfer records
