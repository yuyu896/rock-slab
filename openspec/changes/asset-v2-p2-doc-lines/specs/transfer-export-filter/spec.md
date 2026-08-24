# transfer-export-filter 增量

## MODIFIED Requirements

### Requirement: Transfer export with filter parameters
The system SHALL support exporting transfer records with filter parameters (branch, status, type) passed to the backend API, returning a complete filtered Excel file. Export MUST expand one output row per detail line (单头信息随行重复)，值按行取数（编号/名称/规格/单位/类目联字典回显），模板列保持不变；筛选语义不变。

#### Scenario: Export with branch filter
- **WHEN** user selects a branch filter and clicks "导出" on any transfer type page
- **THEN** the system calls `exportTransfers` API with the selected branch parameter and downloads the filtered Excel file

#### Scenario: Export with status filter
- **WHEN** user selects a status filter and clicks "导出"
- **THEN** the exported Excel contains only records matching the selected status

#### Scenario: Multi-line document expands to multiple rows
- **WHEN** the filtered result contains a purchase document with 3 detail lines
- **THEN** the exported Excel contains 3 rows for that document, each carrying the header fields (单号/日期/分公司/供应商) repeated

## REMOVED Requirements

### Requirement: Purchase page export button
**Reason**: 旧版采购页（`Purchase.vue`）整体清退，其导出入口随页面移除（资产模型 V2 P2 明细行化：旧页的多行表单能力已由新版采购页原生承载）。
**Migration**: `/assets/purchase` 重定向到 `/transfers/purchase`，导出经由采购列表页既有导出按钮（本 spec 第一节）完成。
