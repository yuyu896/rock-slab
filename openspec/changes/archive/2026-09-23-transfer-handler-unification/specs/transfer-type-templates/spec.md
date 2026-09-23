## MODIFIED Requirements

### Requirement: Transfer model has fields for all template columns
The Transfer model SHALL include additional fields to support purchase and assign template columns: 供应商, 单价, 总金额, 需求部门, 经办人 (renamed from `采购经办人`; the single shared handler field for all document types), 用途.

#### Scenario: Purchase transfer stores all template fields
- **WHEN** a purchase transfer is created via import or form
- **THEN** the system SHALL store 供应商, 单价, 总金额, 需求部门, 经办人 alongside existing fields

#### Scenario: Assign transfer stores all template fields
- **WHEN** an assign transfer is created via import or form
- **THEN** the system SHALL store 用途 alongside existing fields
