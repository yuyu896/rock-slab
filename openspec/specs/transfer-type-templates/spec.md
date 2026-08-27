# transfer-type-templates Specification

## Purpose
TBD - created by archiving change fix-transfer-templates-and-warehousing. Update Purpose after archive.
## Requirements
### Requirement: Purchase import template uses dedicated columns
The system SHALL generate the purchase import template with the following columns in order: 采购日期、分公司、资产编号、物品名称、规格型号、图片、供应商、采购数量、单价、总金额、需求部门、采购经办人、备注.

#### Scenario: Download purchase template
- **WHEN** user downloads the purchase import template
- **THEN** the generated Excel file SHALL have exactly these 14 columns: 采购日期, 分公司, 资产编号, 物品名称, 规格型号, 图片, 供应商, 采购数量, 单价, 总金额, 需求部门, 采购经办人, 备注

#### Scenario: Import with purchase template
- **WHEN** user imports an Excel file using the purchase template
- **THEN** the system SHALL map each column to the corresponding Transfer model field and create records with `action_type = purchase`

### Requirement: Assign import template uses dedicated columns
The system SHALL generate the assign (领用) import template with the following columns in order: 分公司、日期、资产编号、领用物品、领用数量、使用人、领用部门、用途、备注. The 使用人 column SHALL map to the line-level 使用人 field (mandatory, in line with the assign form contract); the 领用部门 column SHALL both populate the document-level 调出部门 text AND resolve to the line-level department foreign key by (分公司, 部门名称) — resolution failure MUST reject the row with a per-row error naming the branch and department. Rows missing 使用人 or 领用部门 MUST be rejected (领用行必填不分管理方式).

#### Scenario: Download assign template
- **WHEN** user downloads the assign import template
- **THEN** the generated Excel file SHALL have exactly these columns: 分公司, 日期, 资产编号, 领用物品, 领用数量, 使用人, 领用部门, 用途, 备注

#### Scenario: Import with assign template
- **WHEN** user imports an Excel file using the assign template
- **THEN** the system SHALL map columns to Transfer fields (资产编号→品目字典户籍校验, 领用数量→数量, 使用人→行使用人, 领用部门→单头调出部门+行部门外键) and create records with `action_type = assign`

#### Scenario: Assign row missing 使用人 rejected
- **WHEN** an imported assign row has an empty 使用人 cell
- **THEN** the row SHALL be rejected with a per-row error, no document created for it

#### Scenario: Assign department not found in branch
- **WHEN** an imported assign row names 领用部门「行政部」 which does not exist under the row's 分公司
- **THEN** the row SHALL be rejected with an error naming the branch and department, no document created

### Requirement: Transfer import template uses dedicated columns
The system SHALL generate the transfer (调拨) import template with the following columns: 调拨日期、调出分公司、调出部门、调入分公司、调入部门、资产编号、资产名称、规格型号、调拨数量、调拨原因、调出负责人、调入负责人、备注.

#### Scenario: Download transfer template
- **WHEN** user downloads the transfer import template
- **THEN** the generated Excel file SHALL have exactly these 14 columns: 调拨日期, 调出分公司, 调出部门, 调入分公司, 调入部门, 资产编号, 资产名称, 规格型号, 调拨数量, 调拨原因, 调出负责人, 调入负责人, 备注

#### Scenario: Import with transfer template
- **WHEN** user imports an Excel file using the transfer template
- **THEN** the system SHALL map each column directly to the corresponding Transfer model field and create records with `action_type = transfer`

### Requirement: Export uses type-specific column layouts
The system SHALL export transfer records with column layouts matching their type-specific template definitions.

#### Scenario: Export purchase records
- **WHEN** user exports purchase transfer records
- **THEN** the exported Excel SHALL use the purchase column layout

#### Scenario: Export assign records
- **WHEN** user exports assign transfer records
- **THEN** the exported Excel SHALL use the assign column layout, with "部门累计领用" and "当前库存" as additional computed columns

#### Scenario: Export transfer records
- **WHEN** user exports transfer records
- **THEN** the exported Excel SHALL use the transfer column layout

### Requirement: Transfer model has fields for all template columns
The Transfer model SHALL include additional fields to support purchase and assign template columns: 供应商, 单价, 总金额, 需求部门, 采购经办人, 用途.

#### Scenario: Purchase transfer stores all template fields
- **WHEN** a purchase transfer is created via import or form
- **THEN** the system SHALL store 供应商, 单价, 总金额, 需求部门, 采购经办人 alongside existing fields

#### Scenario: Assign transfer stores all template fields
- **WHEN** an assign transfer is created via import or form
- **THEN** the system SHALL store 用途 alongside existing fields

