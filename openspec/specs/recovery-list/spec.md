# recovery-list Specification

## Purpose
资产回收记录的列表、字段、筛选、导出与回收入口（含资产明细/固定资产行内直接回收）。

## Requirements

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


### Requirement: 从资产明细与固定资产列表行内直接回收
资产明细与固定资产列表 SHALL 在每行操作区提供「回收」入口（仅持 `manage_assets` 权限的用户可见）。点击后弹窗预填该行资产信息（资产编号、资产名称、分公司、部门；固定资产场景数量固定为 1 并携带内部编号，明细场景数量可填且不超过该行数量），用户补充回收分类、出库日期、存放位置、备注后提交。系统 SHALL 创建 `审批状态=已通过` 的回收单（审批人记为操作者）并在同一事务内即时执行回收联动（扣台账、扣明细、删固定资产实例），单据随后出现在回收列表。直接回收 MUST 受盘点锁约束（相关分公司盘点锁定时拒绝），无 `manage_assets` 权限的请求 MUST 被拒绝。

#### Scenario: 资产明细行内回收即时生效
- **WHEN** 持 `manage_assets` 权限的用户在资产明细列表某行点击「回收」，填写数量 2 并提交
- **THEN** 系统生成已通过的回收单，台账与该明细数量即时扣减 2，列表刷新后数量更新

#### Scenario: 固定资产行内回收后记录消失
- **WHEN** 用户对固定资产列表中某实例行点击「回收」并确认
- **THEN** 生成已通过的回收单，该实例记录从固定资产表删除，台账对应行扣减 1

#### Scenario: 无权限用户不可用
- **WHEN** 不持 `manage_assets` 权限的用户查看资产明细列表或以 `immediate` 方式调用回收接口
- **THEN** 列表行内不显示「回收」按钮，接口请求返回权限不足

#### Scenario: 盘点锁定时拒绝直接回收
- **WHEN** 相关分公司存在进行中的盘点任务，用户发起行内直接回收
- **THEN** 系统拒绝并提示分公司盘点锁定中
