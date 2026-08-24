# fixed-asset-table-columns Specification（修改）

## REMOVED Requirements

### Requirement: 固定资产表展示19列
**Reason**: 19 列含大量从 Asset 手抄继承的品目文本列，违反铁律 1；随 FixedAsset 重塑（item 外键 + 出生行派生）整体换为新列布局。
**Migration**: 新列布局见 ADDED；旧 19 列数据由迁移搬迁（品目→item 联查、供应商/单价/购入金额→备注折叠或出生行派生）。

### Requirement: 新增表单覆盖实例可编辑字段
**Reason**: 手动创建入口冻结——实例出生=采购单或存量迁移（fixed-asset-instance delta）。
**Migration**: 前端新增弹窗与入口移除；新增实例改走采购入库单。

### Requirement: 导出包含19列
**Reason**: 随列布局重塑同步替换。
**Migration**: 导出改为新列布局（见 fixed-asset-export delta）。

### Requirement: 导入模板与解析一致
**Reason**: 导入冻结（绕过单据写实例违反实例层铁律）。
**Migration**: 模板下载与导入端点下线（见 fixed-asset-import delta）。

## ADDED Requirements

### Requirement: 实例表新列布局

固定资产实例表 SHALL 展示：序号、分公司、内部编号、品目编号、品目名称、规格、序列号（空=「待补录」醒目标识）、当前状态、使用人、部门、入库日期、供应商（出生行派生，存量为备注折叠值则空）、采购日期（出生行派生）。筛选 MUST 支持：分公司、状态、品目（编号/名称关键字）、序列号待补录。操作列 MUST 仅含「补录」（`manage_instances` 权限者可见）与「生平」。

#### Scenario: 新列表头展示

- **WHEN** 用户打开固定资产实例页
- **THEN** 表头按新列布局展示，品目列由 item 联查、供应商/采购日期由出生行派生

#### Scenario: 待补录标识与筛选

- **WHEN** 某实例序列号为空，用户筛选「待补录」
- **THEN** 该行序列号列显示醒目的「待补录」标识，且出现在筛选结果中

#### Scenario: 补录弹窗

- **WHEN** 持 `manage_instances` 权限的用户点击某实例「补录」
- **THEN** 弹窗仅含 序列号/备注 两字段，提交后列表刷新，标识消失
