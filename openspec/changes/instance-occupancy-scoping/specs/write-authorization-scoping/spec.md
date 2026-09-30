## ADDED Requirements

### Requirement: 实例占用查询限定授权范围

`GET /api/transfers/instance-occupancy`（建单点选器的占用标注辅助读）MUST 对请求的 `branch`（分公司名）做授权范围校验：分公司名可解析时，其分公司 MUST 在操作者授权范围内（admin/「全部数据」授权豁免），范围外 MUST 返回 400 且不返回任何实例/单据信息；分公司名不可解析或参数缺失时 SHALL 返回空列表 `[]`（维持既有语义，不引入额外存在性信号）。该接口 MUST NOT 向无权用户返回范围外分公司的实例内部编号与在途单据信息。

#### Scenario: 范围外分公司查询被拒

- **WHEN** 仅持本分公司范围的用户以他分公司名查询 instance-occupancy
- **THEN** 系统返回 400（授权范围提示），响应不含任何实例编号/单据号

#### Scenario: 范围内分公司查询正常

- **WHEN** 用户以其授权范围内分公司名查询
- **THEN** 系统返回 200 与该分公司实例的占用标注数据（无占用实例不出现在结果中，行为同现状）

#### Scenario: admin 与全部数据授权全量可用

- **WHEN** admin 或持「全部数据」授权的用户以任意分公司名查询
- **THEN** 系统返回 200 与占用数据

#### Scenario: 未知分公司名与缺参返回空

- **WHEN** 查询的 branch 名不存在，或 branch/asset_code 缺失
- **THEN** 系统返回 200 与 `[]`
