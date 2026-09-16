# report-metrics 增量

## ADDED Requirements

### Requirement: 资产总览与分公司报表内容区分

「资产总览」tab SHALL 仅呈现指标卡与图表（总资产/总值/活跃率/库存不足 + 分公司排行 + 分类分布），MUST NOT 再渲染分公司明细表格（与分公司报表重复）。「分公司报表」tab SHALL 渲染分公司明细表格且容器定高：max-height 560px、内容内部滚动、表头 sticky 常驻——页面总长 MUST NOT 随分公司数量无限增长。

#### Scenario: 总览无表格

- **WHEN** 用户切到「资产总览」tab
- **THEN** 页面为指标卡 + 图表，无分公司明细表格

#### Scenario: 分公司表格定高滚动

- **WHEN** 「分公司报表」tab 渲染 72 家分公司
- **THEN** 表格容器高度 ≤560px，滚动查看全部行且滚动中表头常驻
