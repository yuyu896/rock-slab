## ADDED Requirements

### Requirement: Asset template download SHALL return valid Excel with correct headers
系统 SHALL 通过 `GET /api/assets/template` 返回资产导入模板文件。

#### Scenario: Download asset import template
- **WHEN** 已认证用户请求 `GET /api/assets/template`
- **THEN** 返回 HTTP 200，Content-Type 为 Excel 格式，文件可被 openpyxl 解析，第一行包含资产模块导入所需的全部列名（序号、分公司、资产编号、分公司编号、资产类目、电脑序列号、供应商、物品分类、资产名称、图片、入库日期、是否租用、数量、规格、单价、购入金额、出库日期、所属部门、使用人、当前状态、警戒线、是否充足、备注）

### Requirement: Asset batch import SHALL correctly persist all fields
系统 SHALL 通过 `POST /api/assets/import` 接受 Excel 文件并正确入库所有字段。

#### Scenario: Import valid asset Excel file
- **WHEN** 已认证用户上传包含 3 条资产数据的 Excel 文件至 `POST /api/assets/import`
- **THEN** 返回 HTTP 200，响应包含 `{ imported: 3, errors: [] }`，数据库新增 3 条 Asset 记录且所有字段值与上传数据一致

#### Scenario: Import empty Excel file
- **WHEN** 已认证用户上传只有表头无数据行的 Excel 文件
- **THEN** 返回 HTTP 200，响应包含 `{ imported: 0, errors: [] }`

#### Scenario: Import non-Excel file
- **WHEN** 已认证用户上传 .txt 文件
- **THEN** 返回 HTTP 400，响应包含明确的错误信息

### Requirement: Asset export SHALL return complete data with correct columns
系统 SHALL 通过 `GET /api/assets/export` 导出资产列表为 Excel 文件。

#### Scenario: Export assets with existing data
- **WHEN** 已认证用户请求 `GET /api/assets/export` 且数据库中存在资产记录
- **THEN** 返回 HTTP 200，Content-Type 为 Excel 格式，数据行数与资产总数匹配，表头列名与列表页一致

#### Scenario: Export assets with no data
- **WHEN** 已认证用户请求 `GET /api/assets/export` 且数据库中无资产记录
- **THEN** 返回 HTTP 200，Excel 文件仅包含表头行

---

### Requirement: FixedAsset template download SHALL return valid Excel
系统 SHALL 通过 `GET /api/assets/fixed-assets/template` 返回固定资产导入模板文件。

#### Scenario: Download fixed-asset import template
- **WHEN** 已认证用户请求 `GET /api/assets/fixed-assets/template`
- **THEN** 返回 HTTP 200，文件可被 openpyxl 解析，第一行包含固定资产导入所需的全部列名

### Requirement: FixedAsset batch import SHALL correctly persist all fields
系统 SHALL 通过 `POST /api/assets/fixed-assets/import` 接受 Excel 文件并正确入库。

#### Scenario: Import valid fixed-asset Excel file
- **WHEN** 已认证用户上传包含固定资产数据的 Excel 文件
- **THEN** 返回 HTTP 200，数据库新增对应数量的 FixedAsset 记录

---

### Requirement: Category template download SHALL return valid Excel with correct headers
系统 SHALL 通过 `GET /api/categories/template` 返回分类导入模板文件。

#### Scenario: Download category import template
- **WHEN** 已认证用户请求 `GET /api/categories/template`
- **THEN** 返回 HTTP 200，第一行包含分类导入所需的列名（资产类目、物品分类、资产名称、资产编号、计量单位、警戒线、备注）

### Requirement: Category batch import SHALL correctly persist all fields
系统 SHALL 通过 `POST /api/categories/import` 接受 Excel 文件并正确入库。

#### Scenario: Import valid category Excel file
- **WHEN** 已认证用户上传包含分类数据的 Excel 文件
- **THEN** 返回 HTTP 200，数据库新增对应数量的 Category 记录，所有字段正确

#### Scenario: Import category with duplicate asset_code
- **WHEN** 已认证用户上传包含已存在资产编号的分类数据
- **THEN** 系统更新已有记录而非创建重复记录

### Requirement: Category export SHALL return complete data
系统 SHALL 通过 `GET /api/categories/export` 导出分类数据。

#### Scenario: Export categories with existing data
- **WHEN** 已认证用户请求 `GET /api/categories/export` 且数据库中存在分类记录
- **THEN** 返回 HTTP 200，Excel 数据行数与分类总数匹配

---

### Requirement: Transfer template download SHALL return type-specific headers
系统 SHALL 通过 `GET /api/transfers/template?type=<type>` 返回对应类型的导入模板，支持 purchase/assign/transfer/recovery 四种类型。

#### Scenario: Download purchase template
- **WHEN** 已认证用户请求 `GET /api/transfers/template?type=purchase`
- **THEN** 返回 HTTP 200，表头包含采购导入所需的列名（采购日期、分公司、资产编号等）

#### Scenario: Download assign template
- **WHEN** 已认证用户请求 `GET /api/transfers/template?type=assign`
- **THEN** 返回 HTTP 200，表头包含领用导入所需的列名

#### Scenario: Download transfer template
- **WHEN** 已认证用户请求 `GET /api/transfers/template?type=transfer`
- **THEN** 返回 HTTP 200，表头包含调拨导入所需的列名

#### Scenario: Download recovery template
- **WHEN** 已认证用户请求 `GET /api/transfers/template?type=recovery`
- **THEN** 返回 HTTP 200，表头包含回收导入所需的列名（含回收分类、单位、出库日期、存放位置、资产类目、物品分类）

### Requirement: Transfer batch import SHALL persist all fields including recovery/purchase specific fields
系统 SHALL 通过 `POST /api/transfers/import?type=<type>` 接受 Excel 文件，所有类型特有的字段 MUST 正确入库。

#### Scenario: Import purchase transfers with all fields
- **WHEN** 已认证用户上传包含采购数据的 Excel 文件至 `POST /api/transfers/import?type=purchase`
- **THEN** 数据库中可查到对应记录，且 供应商、单价、总金额、需求部门、采购经办人、用途 等采购特有字段值正确

#### Scenario: Import recovery transfers with all fields
- **WHEN** 已认证用户上传包含回收数据的 Excel 文件至 `POST /api/transfers/import?type=recovery`
- **THEN** 数据库中可查到对应记录，且 回收分类、单位、出库日期、存放位置、资产类目、物品分类 等回收特有字段值正确

#### Scenario: Import assign transfers
- **WHEN** 已认证用户上传包含领用数据的 Excel 文件至 `POST /api/transfers/import?type=assign`
- **THEN** 返回 HTTP 200，数据库新增对应记录

#### Scenario: Import transfer type transfers
- **WHEN** 已认证用户上传包含调拨数据的 Excel 文件至 `POST /api/transfers/import?type=transfer`
- **THEN** 返回 HTTP 200，数据库新增对应记录

### Requirement: Transfer export SHALL return type-specific data
系统 SHALL 通过 `GET /api/transfers/export?type=<type>` 导出对应类型的调拨数据。

#### Scenario: Export purchase transfers
- **WHEN** 已认证用户请求 `GET /api/transfers/export?type=purchase` 且存在采购记录
- **THEN** 返回 HTTP 200，Excel 仅包含采购类型的记录，数据行数匹配

#### Scenario: Export recovery transfers
- **WHEN** 已认证用户请求 `GET /api/transfers/export?type=recovery` 且存在回收记录
- **THEN** 返回 HTTP 200，Excel 仅包含回收类型的记录

---

### Requirement: Inventory template download SHALL return valid Excel per task
系统 SHALL 通过 `GET /api/inventories/{id}/import-template` 返回特定盘点任务的导入模板。

#### Scenario: Download inventory import template for existing task
- **WHEN** 已认证用户请求已有盘点任务的模板下载
- **THEN** 返回 HTTP 200，Excel 文件包含该任务关联资产的表头

### Requirement: Inventory batch import SHALL update inventory results
系统 SHALL 通过 `POST /api/inventories/{id}/import-result` 接受盘点结果 Excel 并更新盘点项。

#### Scenario: Import valid inventory results
- **WHEN** 已认证用户上传包含盘点结果的 Excel 文件
- **THEN** 返回 HTTP 200，对应盘点项的实际数量和结果被正确更新

---

### Requirement: Import export tests SHALL handle edge cases gracefully
所有导入端点 SHALL 对异常输入返回明确的错误信息而非服务端崩溃。

#### Scenario: Upload file with special characters in data
- **WHEN** 已认证用户上传包含换行符、引号、逗号的数据
- **THEN** 系统正确处理特殊字符，数据入库后值与上传一致

#### Scenario: Upload file with missing required fields
- **WHEN** 已认证用户上传缺少必填列的 Excel 文件
- **THEN** 返回 HTTP 400 或在响应 errors 中明确指出缺失的列
