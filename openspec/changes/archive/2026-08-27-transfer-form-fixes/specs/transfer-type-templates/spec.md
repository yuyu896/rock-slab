## MODIFIED Requirements

### Requirement: Assign import template uses dedicated columns
The system SHALL generate the assign (领用) import template with the following columns in order: 分公司、日期、资产编号、领用物品、领用数量、使用人、领用部门、用途、备注. The 使用人 column SHALL map to the line-level 使用人 field (mandatory, in line with the assign form contract); the 领用部门 column SHALL both populate the document-level 调出部门 text AND resolve to the line-level department foreign key by (分公司, 部门名称) — resolution failure MUST reject the row with a per-row error naming the branch and department. Rows missing 使用人 or 领用部门 MUST be rejected (领用行必填不分管理方式).

#### Scenario: Download assign template
- **WHEN** user downloads the assign import template
- **THEN** the generated Excel file SHALL have exactly these 9 columns: 分公司, 日期, 资产编号, 领用物品, 领用数量, 使用人, 领用部门, 用途, 备注

#### Scenario: Import with assign template
- **WHEN** user imports an Excel file using the assign template
- **THEN** the system SHALL map columns to Transfer fields (资产编号→品目字典户籍校验, 领用数量→数量, 使用人→行使用人, 领用部门→单头调出部门+行部门外键) and create records with `action_type = assign`

#### Scenario: Assign row missing 使用人 rejected
- **WHEN** an imported assign row has an empty 使用人 cell
- **THEN** the row SHALL be rejected with a per-row error, no document created for it

#### Scenario: Assign department not found in branch
- **WHEN** an imported assign row names 领用部门「行政部」 which does not exist under the row's 分公司
- **THEN** the row SHALL be rejected with an error naming the branch and department, no document created
