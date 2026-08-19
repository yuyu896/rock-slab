# fa-import-dedup-drop-user Specification

## Purpose
TBD - created by archiving change fa-import-dedup-drop-user. Update Purpose after archive.
## Requirements
### Requirement: 固定资产导入去重不含使用人
固定资产导入的去重判定 SHALL 不含使用人——按 `(分公司 + 分公司编号 + 电脑序列号 + 所属部门)` 四元组全同才算重复。

#### Scenario: 同设备不同使用人不算重复
- **WHEN** 两行分公司/编号/序列号/所属部门全同、但使用人不同
- **THEN** 两行都导入成功（使用人不参与去重）

