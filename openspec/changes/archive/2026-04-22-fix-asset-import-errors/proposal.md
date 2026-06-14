## Why

资产批量导入时，错误提示是原始的数据库/DRF 错误信息（如 `UNIQUE constraint failed: assets_asset.资产编号`、`'"/"'的值应该是一个十进制数字。'`），用户完全无法理解问题在哪里、怎么修正。同时导入代码缺少对 Excel 数据格式的预处理，导致日期（Excel 序列号）、布尔值（"是"/"否"）、空字段等无法正确解析。

## What Changes

- 资产导入增加数据预处理：Excel 日期序列号转 Python date、布尔值 "是"/"否" 转 True/False、"无"/空字符串跳过
- UNIQUE constraint 冲突时显示「资产编号 XXX 已存在，请修改或删除重复行」
- 字段验证错误时显示中文列名和具体值（如「单价字段值 "/" 不是有效数字」）
- 同类错误合并显示（避免 70 行重复报同样的错），汇总为「第 3-26 行: 资产编号 A-a00011 已存在（共 24 行）」
- 分类导入、采购导入等也应用同样的错误友好化逻辑

## Capabilities

### New Capabilities
- `import-error-friendly`: 资产/分类/流转批量导入时，将原始错误转换为中文可读提示，同类错误合并显示

### Modified Capabilities

## Impact

- **后端**: `assets/views.py` import_excel — 数据预处理 + 错误捕获友好化
- **后端**: `categories/views.py`、`transfers/views.py` 的 import_excel — 同样优化
- **前端**: 导入弹窗的错误展示可能需要适配（如果后端返回格式变了）
