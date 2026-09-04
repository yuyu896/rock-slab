# export-filter-alignment 增量

## MODIFIED Requirements

### Requirement: 资产汇总与品目导出维持筛选遵循
资产汇总页导出 MUST 携带分公司（branch）、资产类目（category）、关键词（keyword）；品目页导出 MUST 携带页面当前全部筛选：资产类目（资产类目）、物品分类（物品分类）、管理方式（管理方式）、关键词（keyword），空筛选不传参。

#### Scenario: 资产汇总分类筛选导出
- **WHEN** 用户在资产汇总页筛选资产类目后导出
- **THEN** 导出请求携带 category，Excel 仅含该类目的台账行

#### Scenario: 品目管理方式筛选参与导出
- **WHEN** 用户在品目页筛选管理方式「消耗品」后导出
- **THEN** 导出请求携带管理方式参数，Excel 仅含消耗品品目

#### Scenario: 品目物品分类筛选参与导出
- **WHEN** 用户在品目页筛选物品分类「办公设备」后导出
- **THEN** 导出请求携带物品分类参数，Excel 仅含该物品分类的品目
