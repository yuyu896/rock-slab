# fa-template-check-and-seqno Specification

## Purpose
TBD - created by archiving change fa-template-check-and-seqno. Update Purpose after archive.
## Requirements
### Requirement: 固定资产导入校验表头一致
固定资产导入 SHALL 校验上传 Excel 的表头与模板（FA_TEMPLATE_HEADERS）列名集合一致；不一致 → 拒绝并提示缺少/多余的列名。

#### Scenario: 表头不一致被拒
- **WHEN** 上传的 Excel 表头与模板列名集合不同（多列或少列）
- **THEN** 返回错误提示，不导入任何数据

#### Scenario: 表头一致（顺序不同）可导入
- **WHEN** 上传的 Excel 表头列名与模板相同但顺序不同
- **THEN** 正常导入

### Requirement: 固定资产列表序号为计算行号
固定资产列表序号 SHALL 显示当前分页内的计算行号 `(page-1)*pageSize + index + 1`，与资产列表一致。

#### Scenario: 序号显示行号
- **WHEN** 查看固定资产列表
- **THEN** 序号列显示连续行号（非'-'）

