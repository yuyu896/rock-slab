# fa-layout-and-print Specification

## Purpose
TBD - created by archiving change fa-layout-and-print. Update Purpose after archive.
## Requirements
### Requirement: 固定资产表布局自适应
固定资产表页面 SHALL 在窄窗口下表格可水平滚动（不被裁剪）。

#### Scenario: 窄窗口表格可滚动
- **WHEN** 浏览器窗口宽度不足以显示全部列
- **THEN** 表格可水平滚动查看所有列（不被 hidden 裁剪）

### Requirement: 固定资产表标签打印
固定资产表 SHALL 支持标签打印——行内「打印标签」按钮 + 批量栏「打印标签」+ 打印弹窗。

#### Scenario: 单行打印标签
- **WHEN** 用户点击某固定资产行的「打印标签」
- **THEN** 弹出打印预览/打印该行标签

#### Scenario: 批量打印标签
- **WHEN** 用户勾选多条后点批量栏「打印标签」
- **THEN** 打印所选多条标签

