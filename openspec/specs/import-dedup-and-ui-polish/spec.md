# import-dedup-and-ui-polish Specification

## Purpose
TBD - created by archiving change import-dedup-and-ui-polish. Update Purpose after archive.
## Requirements
### Requirement: 固定资产导入 DB 级查重
固定资产导入每行 SHALL 检查 DB 是否已存在相同四元组（分公司+分公司编号+电脑序列号+所属部门），存在则跳过并提醒。

#### Scenario: 重复数据被拒
- **WHEN** 导入一行数据，DB 已存在相同四元组
- **THEN** 该行跳过，结果提示「已存在」

### Requirement: 导入行数限制
批量导入超过 200 行时 SHALL 拒绝导入并提示分批。

#### Scenario: 超限被拒
- **WHEN** 导入文件超过 200 行
- **THEN** 返回 400 提示「数据量过大，建议分批导入」

### Requirement: 操作按钮加大
资产列表和固定资产表的操作按钮 SHALL 图标和按钮尺寸加大，清晰可辨。

#### Scenario: 按钮清晰可点
- **WHEN** 用户查看操作列
- **THEN** 编辑/删除/打印按钮图标清晰可见、易于点击

### Requirement: 资产列表滚动条始终可见
资产列表表格 SHALL 在固定高度内滚动，横向滚动条始终可见。

#### Scenario: 滚动条可见
- **WHEN** 用户打开资产列表
- **THEN** 无需先滚到底即可看到横向滚动条

