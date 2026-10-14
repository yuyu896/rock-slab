## MODIFIED Requirements

### Requirement: Export fixed assets to Excel

用户点击导出按钮后，系统 SHALL 将当前筛选条件下的普通固定资产档案导出为 Excel 文件并触发浏览器下载。导出列 MUST 与实例表新列布局一致（序号、分公司、内部编号、品目编号、品目名称、规格、序列号、当前状态、使用人、部门、入库日期、供应商、采购日期），品目列经 item 联查、供应商/采购日期经出生行派生。所有导出结果 MUST 排除已关联已生效直接处置回收明细的实例；排除条件不得仅依据“退役”状态。

#### Scenario: Export with active filters

- **WHEN** 用户设置分公司或状态筛选条件后点击导出
- **THEN** 系统请求导出接口并传入当前筛选参数，下载数据符合筛选条件且排除已生效直接处置实例

#### Scenario: Export with no filters

- **WHEN** 用户未设置任何筛选条件时点击导出
- **THEN** 系统导出全部普通固定资产档案，排除已生效直接处置实例，但保留其他退役实例

#### Scenario: Export failure

- **WHEN** 导出接口返回错误
- **THEN** 页面显示错误提示消息

#### Scenario: 导出列与新列表一致

- **WHEN** 用户导出 Excel
- **THEN** 表头与新列布局一致，序列号为空者输出“待补录”
