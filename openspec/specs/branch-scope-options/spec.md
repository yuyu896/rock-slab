# branch-scope-options Specification

## Purpose
分公司选项接口的范围下发：`GET /api/branches?scope=write` 按操作者管理授权（resolve_user_scope）服务端过滤，供写单页扣数方分公司下拉收口；无参维持全量兼容既有调用方。

## Requirements
### Requirement: 分公司选项接口支持授权范围过滤

`GET /api/branches` SHALL 支持查询参数 `scope`。`scope=write` 时服务端 MUST 按 `resolve_user_scope(request.user)` 过滤，仅返回授权范围内分公司集合内的分公司（admin 与持「全部数据」授权用户豁免，返回全量；无任何授权的用户返回空列表）。无 `scope` 参数时 MUST 维持全量下发，不改变既有调用方（列表筛选、组织管理、权限分配页、调拨调入方下拉等）的行为。

#### Scenario: 范围受限用户请求 scope=write 仅得授权分公司

- **WHEN** 数据范围仅含区域 A（旗下分公司 A1、A2）的 manager 请求 `GET /api/branches?scope=write`
- **THEN** 响应仅含 A1、A2，不含其他区域分公司

#### Scenario: admin 请求 scope=write 得全量

- **WHEN** admin 用户请求 `GET /api/branches?scope=write`
- **THEN** 响应包含全部分公司（豁免过滤）

#### Scenario: 无参请求维持全量

- **WHEN** 范围受限用户请求 `GET /api/branches`（不带 scope 参数）
- **THEN** 响应仍为全部分公司，既有筛选与管理页面行为不变

#### Scenario: 无授权用户请求 scope=write 得空列表

- **WHEN** 无任何管理授权且非 admin 的用户请求 `GET /api/branches?scope=write`
- **THEN** 响应为空列表（没有可写单的分公司，与提交端 `validate_branches_in_scope` 口径一致）
