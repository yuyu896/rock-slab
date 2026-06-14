## ADDED Requirements

### Requirement: Recovery list page
系统 SHALL 在资产流转菜单下提供"回收"入口，点击后显示回收记录列表页面，路由为 `/transfers/recovery`。

#### Scenario: User navigates to recovery list
- **WHEN** 用户点击侧边栏"资产流转"下的"回收"菜单项
- **THEN** 系统导航到 `/transfers/recovery`，显示回收记录列表页面

### Requirement: Recovery list table columns
回收列表 SHALL 按以下顺序显示表头列：序号、分公司、资产编号、资产类目、物品分类、资产名称、回收分类、入库日期、数量、单位、规格、出库日期、所属部门、当前处理状态、存放位置、经办人、备注。

#### Scenario: Recovery list displays all columns
- **WHEN** 回收列表有数据时
- **THEN** 表格按顺序显示 17 列：序号（行号）、分公司（调出分公司）、资产编号、资产类目、物品分类、资产名称、回收分类、入库日期（调拨日期）、数量（调拨数量）、单位、规格（规格型号）、出库日期、所属部门（调出部门）、当前处理状态（审批状态）、存放位置、经办人（采购经办人）、备注

### Requirement: Recovery action type
Transfer 模型 SHALL 支持 `recovery` 操作类型，作为 ACTION_CHOICES 的新选项。

#### Scenario: Create recovery record
- **WHEN** 用户在回收页面新建回收记录
- **THEN** 系统创建 action_type 为 `recovery` 的 Transfer 记录

### Requirement: Recovery new fields
Transfer 模型 SHALL 新增以下可选字段以支持回收功能：回收分类（CharField）、单位（CharField）、出库日期（DateField）、存放位置（CharField）、资产类目（CharField）、物品分类（CharField）。

#### Scenario: Recovery record with new fields
- **WHEN** 创建回收记录并填写回收分类、单位、出库日期、存放位置、资产类目、物品分类
- **THEN** 这些字段值被正确保存并可读取

### Requirement: Recovery category choices
回收分类字段 SHALL 提供以下选项：闲置回收、报废回收、捐赠回收、其他。

#### Scenario: User selects recovery category
- **WHEN** 用户在新建回收记录时选择回收分类
- **THEN** 下拉框显示"闲置回收"、"报废回收"、"捐赠回收"、"其他"四个选项

### Requirement: Recovery list filtering and pagination
回收列表 SHALL 支持按状态筛选、按分公司筛选、关键词搜索，以及标准分页。

#### Scenario: Filter recovery records by status
- **WHEN** 用户选择审批状态筛选条件
- **THEN** 列表仅显示匹配状态的回收记录

#### Scenario: Paginate recovery records
- **WHEN** 回收记录超过每页条数
- **THEN** 底部分页组件显示总条数和页码导航

### Requirement: Recovery export
回收列表 SHALL 支持导出为 Excel 文件，导出内容与列表表头一致。

#### Scenario: Export recovery records
- **WHEN** 用户点击导出按钮
- **THEN** 系统下载包含回收记录的 Excel 文件，列头与列表一致

### Requirement: Recovery sidebar entry
侧边栏资产流转分组下 SHALL 新增"回收"菜单项，位于"调拨"之后。

#### Scenario: Sidebar shows recovery menu
- **WHEN** 用户展开侧边栏"资产流转"分组
- **THEN** 显示"采购入库"、"领用出库"、"调拨"、"回收"四个子菜单项
