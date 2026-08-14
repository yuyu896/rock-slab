## ADDED Requirements

### Requirement: 按分公司汇总资产编号接口
系统 SHALL 提供 `GET /api/assets/summary/` 接口，返回当前用户管理授权范围内各分公司的资产汇总：分公司名称、分公司编码、资产总数、资产编号最小值、资产编号最大值，按分公司编码排序。数据隔离语义 MUST 与报表接口一致（admin 或「全部数据」授权见全集；其余仅见授权分公司；无授权返回空数组）。

#### Scenario: admin 获取全部分公司汇总
- **WHEN** admin 已登录且调用 `GET /api/assets/summary/`
- **THEN** 返回所有有资产的分公司的名称、编码、资产总数与编号起止，按分公司编码排序

#### Scenario: 按授权范围隔离
- **WHEN** 仅持有分公司 A、B 授权的用户调用 `GET /api/assets/summary/`，而系统存在分公司 A、B、C 的资产
- **THEN** 返回结果只包含分公司 A、B 的汇总行

#### Scenario: 无授权用户
- **WHEN** 无任何管理授权的非 admin 用户调用 `GET /api/assets/summary/`
- **THEN** 返回空数组（HTTP 200）

### Requirement: 资产汇总页面
系统 SHALL 在 `/assets/summary` 提供「资产汇总」页面，以表格展示各分公司的资产编号汇总（模板版维度：分公司、编码、资产总数、编号起始、编号截止），并在底部展示合计行。

#### Scenario: 查看资产汇总
- **WHEN** 已登录用户进入「库存 → 资产汇总」
- **THEN** 页面标题为「资产汇总」，表格按分公司列出资产总数与编号起止，底部显示全部合计

#### Scenario: 空数据
- **WHEN** 用户授权范围内没有任何资产
- **THEN** 页面显示空表格与合计 0，不报错
