## ADDED Requirements

### Requirement: FixedAsset model
系统 MUST 提供 FixedAsset 模型，一条记录代表一台实物实例。每条记录 MUST 包含：内部编号（自动生成，唯一）、资产编号（关联 Asset 品目）、序列号（可空）、供应商、使用人、所属部门、当前状态（在库/在用/空闲）、分公司、入库日期、备注。

#### Scenario: Create fixed asset instance
- **WHEN** 用户为资产编号 COMP-001 新增一条 FixedAsset 实例
- **THEN** 系统自动生成内部编号 COMP-001-1，记录创建成功

#### Scenario: Multiple instances for same asset
- **WHEN** 用户为资产编号 COMP-001 连续新增 3 条实例
- **THEN** 内部编号分别为 COMP-001-1、COMP-001-2、COMP-001-3

### Requirement: Quantity sync to Asset
FixedAsset 实例的创建、删除、状态变更 MUST 自动同步到关联 Asset 的数量字段。Asset.数量 MUST 等于关联 FixedAsset 的总数，Asset 在库数 MUST 等于状态为「在库」的 FixedAsset 数量。

#### Scenario: Create instance updates Asset count
- **WHEN** 为 Asset(COMP-001, 原数量=3) 新增 1 条 FixedAsset 实例
- **THEN** Asset.数量自动更新为 4

#### Scenario: Delete instance updates Asset count
- **WHEN** 删除 Asset(COMP-001, 原数量=5) 的一条 FixedAsset 实例
- **THEN** Asset.数量自动更新为 4

### Requirement: FixedAsset API
系统 MUST 提供 `/api/fixed-assets/` RESTful API，支持列表查询（带筛选/分页）、创建、更新、删除。supervisor(L3) 及以上可执行写操作，leader/staff 只读。

#### Scenario: List fixed assets with filters
- **WHEN** 用户 GET `/api/fixed-assets/?branch=分公司A&status=在用`
- **THEN** 返回该分公司下状态为「在用」的 FixedAsset 实例列表

#### Scenario: Staff cannot create instance
- **WHEN** staff(L5) 用户 POST `/api/fixed-assets/`
- **THEN** 返回 403

### Requirement: Frontend fixed asset page
固定资产表页面 MUST 展示 FixedAsset 实例列表，表格列包含：内部编号、资产编号、资产名称、序列号、供应商、使用人、所属部门、状态。MUST 支持按分公司、状态、关键词筛选和分页。supervisor 及以上 MUST 可执行编辑和删除操作。

#### Scenario: Fixed asset page displays instances
- **WHEN** 用户打开固定资产表页面
- **THEN** 显示所有固定资产实例，每行一台实物

#### Scenario: Edit instance
- **WHEN** supervisor 用户点击某实例的编辑按钮
- **THEN** 打开编辑表单，可修改使用人、状态、供应商等字段

### Requirement: Excel import for fixed assets
系统 MUST 支持通过 Excel 批量导入 FixedAsset 实例，导入模板 MUST 包含：资产编号、序列号、供应商、使用人、所属部门、状态等列。导入时自动生成内部编号并同步 Asset 数量。

#### Scenario: Import creates instances
- **WHEN** 用户上传包含 5 行数据的 FixedAsset 导入 Excel
- **THEN** 创建 5 条 FixedAsset 实例，关联 Asset 的数量自动更新

#### Scenario: Import with invalid asset code
- **WHEN** 导入的 Excel 中包含不存在的资产编号
- **THEN** 返回友好错误提示「资产编号 XXX 不存在」
