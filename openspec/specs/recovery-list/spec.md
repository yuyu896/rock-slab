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

### Requirement: 回收入口唯一化

回收的唯一入口 MUST 是回收单审批流：新建回收单（待审批）→ 审批通过生效。资产明细与固定资产列表 MUST NOT 提供行内回收/即时回收入口；回收创建请求携带 `immediate` 参数 MUST 被拒绝（400），错误信息 MUST 引导走回收单审批流（数据修正走台账调整单），且 MUST NOT 落库。回收语义不变：回收 = 从「在用」收回（在用−N → 回收库+N，或直接处置在用−N），实例退役而非删除，全部经审批生效路径执行。

#### Scenario: 携带 immediate 的回收请求被拒

- **WHEN** 任何用户（含持 `manage_assets` 者）以 `immediate: true` POST 回收创建接口
- **THEN** 返回 400（行内即时回收已下线，引导走回收单审批流），不创建任何单据，台账无变化

#### Scenario: 实例档案页无行内回收入口

- **WHEN** 持 `manage_assets` 权限的用户查看实例档案页（含「在用」实例行）
- **THEN** 行内操作区不出现「回收」按钮；回收经侧边栏「回收」创建页发起

#### Scenario: 普通回收单照常走审批

- **WHEN** 用户经回收创建页提交回收单（不携带 immediate）
- **THEN** 单据落库为待审批，审批通过后台账与实例按既有矩阵联动

### Requirement: 回收单创建在用软预检
回收单创建与编辑（含驳回后编辑、Excel 导入）MUST 对数量管理品目行做在用软预检：按（调出分公司 × 品目）合并计量全部明细行数量，超过该台账行当前在用数量即拒绝（400，不落库），错误信息 MUST 为业务口径（含当前在用与需回收数量，提示核对是否未领用或调出分公司选错）。此为软预检（不持锁）：生效时的行锁充足性终检 MUST 维持不变（覆盖创建后账面变动）。实例管理品目不适用（实例"在用"状态校验已在既有预检矩阵内）。

#### Scenario: 创建超在用被拒
- **WHEN** 调出分公司 A 的品目 X 台账在用为 0，用户提交回收单（X × 1，数量管理品目）
- **THEN** 返回 400（业务文案：当前在用 0，需回收 1），不创建单据

#### Scenario: 多行同品目合并计量
- **WHEN** 品目 X 在用为 3，回收单两行各 X × 2（合计 4）
- **THEN** 返回 400（合计 4 超出当前在用 3）

#### Scenario: 驳回后编辑同样受检
- **WHEN** 已驳回回收单被编辑为超出当前在用的数量并保存
- **THEN** 返回 400，单据保持原状

#### Scenario: 在用足够正常创建
- **WHEN** 品目 X 在用为 2，提交回收单 X × 2
- **THEN** 单据落库为待审批，审批通过后台账正常联动（在用−2）
