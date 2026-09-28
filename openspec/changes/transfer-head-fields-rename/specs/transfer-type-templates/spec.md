## MODIFIED Requirements

### Requirement: Transfer model has fields for all template columns
The Transfer model SHALL include additional fields to support purchase and assign template columns: 供应商, 单价, 总金额, 需求部门, 单据日期 (renamed from `调拨日期`; the shared business date for all five document types — user-facing column labels stay scene-specific: 采购日期/日期/调拨日期/回收日期), 事由 (renamed from `调拨原因`), 用途.

#### Scenario: Purchase transfer stores all template fields
- **WHEN** a purchase transfer is created via import or form
- **THEN** the system SHALL store 供应商, 单价, 总金额, 需求部门, 单据日期 alongside existing fields

#### Scenario: Assign transfer stores all template fields
- **WHEN** an assign transfer is created via import or form
- **THEN** the system SHALL store 用途 alongside existing fields

#### Scenario: 用户可见列标签不随字段改名变化

- **WHEN** 用户下载导入模板或导出 Excel
- **THEN** 列名仍为场景化标签（采购日期/日期/调拨日期/回收日期/调拨原因），与改名前的文件完全兼容
