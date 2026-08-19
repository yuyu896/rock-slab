# export-filter-alignment Specification

## Purpose
TBD - created by archiving change export-respect-filters. Update Purpose after archive.
## Requirements
### Requirement: 导出遵循当前筛选总则
凡提供 Excel 导出按钮的库存与流转列表页（资产明细、固定资产、资产汇总、品目、采购入库、领用出库、调拨、回收），导出的数据集 MUST 与该页面当前生效筛选条件下的列表查询结果一致；未被筛选条件命中的记录 MUST NOT 出现在导出文件中。筛选条件为空时导出全量（数据范围内）。

#### Scenario: 筛选后导出仅含命中数据
- **WHEN** 用户在某列表页设置了任意筛选组合并点击「导出」
- **THEN** 下载的 Excel 仅包含当前列表筛选结果的记录

#### Scenario: 无筛选导出全量
- **WHEN** 用户未设置任何筛选直接点击「导出」
- **THEN** 导出包含其数据范围内全部记录

### Requirement: 资产明细导出透传全部筛选
资产明细页导出请求 MUST 携带页面当前的全部筛选参数：分公司（branch）、资产类目（category）、状态（status）、关键词（keyword），空筛选不传参。

#### Scenario: 分公司加类目筛选导出
- **WHEN** 用户筛选分公司 A、资产类目「固定资产类」后导出
- **THEN** 导出请求携带 branch=分公司A 与 category=固定资产类，Excel 仅含同时满足两条件的资产

#### Scenario: 关键词与状态筛选参与导出
- **WHEN** 用户输入关键词「笔记本」并筛选状态「在库」后导出
- **THEN** 导出请求携带 keyword 与 status，结果仅含命中的在库资产

### Requirement: 固定资产导出透传全部筛选
固定资产表导出请求 MUST 携带页面当前的全部筛选参数：分公司（branch）、状态（status）、关键词（keyword）、资产名称（资产名称），空筛选不传参。

#### Scenario: 资产名称筛选参与导出
- **WHEN** 用户在资产名称筛选框输入「打印机」后导出
- **THEN** 导出请求携带该参数，Excel 仅含资产名称命中「打印机」的固定资产

### Requirement: 流转列表导出透传全部筛选
采购入库、领用出库、调拨、回收四个流转列表的导出请求 MUST 携带页面当前的全部筛选参数：调出分公司（fromBranch）、调入分公司（toBranch）、状态（status）、关键词（keyword），以及页面固有的类型（type）；空筛选不传参。

#### Scenario: 关键词筛选参与流转导出
- **WHEN** 用户在回收列表输入资产编号关键词后导出
- **THEN** 导出请求携带 keyword 与 type=recovery，Excel 仅含命中的回收记录

### Requirement: 资产汇总与品目导出维持筛选遵循
资产汇总页导出 MUST 携带分公司（branch）、资产类目（category）、关键词（keyword）；品目页导出 MUST 携带资产类目与关键词。两页现状已满足，作为规格固化以防回归。

#### Scenario: 资产汇总分类筛选导出
- **WHEN** 用户在资产汇总页筛选资产类目后导出
- **THEN** 导出请求携带 category，Excel 仅含该类目的台账行

