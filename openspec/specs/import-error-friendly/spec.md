# import-error-friendly Specification

## Purpose
TBD - created by archiving change fix-asset-import-errors. Update Purpose after archive.
## Requirements
### Requirement: Excel 日期序列号自动转换
导入时系统 SHALL 将 Excel 日期序列号（整数）自动转换为 Python date 对象。

#### Scenario: 入库日期为 Excel 序列号
- **WHEN** Excel 中入库日期列的值为整数 46057
- **THEN** 系统将其转换为对应的 Python date 对象并正常导入

#### Scenario: 入库日期为字符串
- **WHEN** Excel 中入库日期列的值为字符串 "2026-01-01"
- **THEN** 系统将其解析为 date 对象并正常导入

### Requirement: 布尔值中文自动转换
导入时系统 SHALL 将中文布尔值自动转换：`"是"`/`"true"` → `True`，`"否"`/`"false"`/空 → `False`。

#### Scenario: 是否租用为中文
- **WHEN** Excel 中是否租用列的值为 "否"
- **THEN** 系统将其转换为 False 并正常导入

### Requirement: UNIQUE 冲突显示中文提示
资产编号重复时，系统 SHALL 显示「第 X 行: 资产编号 XXX 已存在，请修改或删除重复行」。

#### Scenario: 资产编号重复
- **WHEN** 导入的资产编号在数据库中已存在
- **THEN** 错误提示包含具体的资产编号和友好的中文说明

### Requirement: 字段验证错误显示中文列名
字段值无效时，系统 SHALL 显示中文列名和无效值，如「单价字段值 "/" 不是有效数字」。

#### Scenario: 数字字段包含非数字值
- **WHEN** 单价列的值为 "/"
- **THEN** 错误提示为「第 X 行: 单价字段值 "/" 不是有效数字」

### Requirement: 同类错误合并显示
多行出现相同错误时，系统 SHALL 合并行号显示。

#### Scenario: 多行资产编号重复
- **WHEN** 第 3-26 行的资产编号都是同一个已存在的编号
- **THEN** 错误提示为「第 3-26 行: 资产编号 XXX 已存在（共 24 行）」

