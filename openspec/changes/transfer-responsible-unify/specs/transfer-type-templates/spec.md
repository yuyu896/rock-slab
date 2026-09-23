## MODIFIED Requirements

### Requirement: Transfer import template uses dedicated columns
The system SHALL generate the transfer (调拨) import template with the following columns: 调拨日期、调出分公司、调出部门、调入分公司、调入部门、资产编号、资产名称、规格型号、调拨数量、调拨原因、调入负责人、备注. The 调出负责人 column SHALL be removed (经办人 is system-defaulted to the import operator, in line with the purchase template); legacy template files containing the removed column SHALL be rejected by the header guard (accepted breakage).

#### Scenario: Download transfer template
- **WHEN** user downloads the transfer import template
- **THEN** the generated Excel file SHALL have exactly these 12 columns: 调拨日期, 调出分公司, 调出部门, 调入分公司, 调入部门, 资产编号, 资产名称, 规格型号, 调拨数量, 调拨原因, 调入负责人, 备注

#### Scenario: Import with transfer template
- **WHEN** user imports an Excel file using the transfer template
- **THEN** the system SHALL map each column directly to the corresponding Transfer model field, set 经办人 to the import operator, and create records with `action_type = transfer`
