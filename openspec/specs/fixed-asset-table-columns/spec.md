# fixed-asset-table-columns Specification

## Purpose
TBD - created by archiving change update-fixed-asset-table-columns. Update Purpose after archive.
## Requirements
### Requirement: 列表查询性能
固定资产表列表查询和导出 SHALL 预加载父级 Asset 品目，避免 N+1 查询。

#### Scenario: 列表查询预加载
- **WHEN** 后端查询 FixedAsset 列表
- **THEN** 查询集 SHALL 使用 `select_related('asset')` 预加载父级品目

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

