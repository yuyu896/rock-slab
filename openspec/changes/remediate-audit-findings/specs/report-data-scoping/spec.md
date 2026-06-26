## ADDED Requirements

### Requirement: 报表查询集必须遵循统一数据范围授权

所有报表接口（资产价值、调拨流水、盘点统计等）SHALL 通过项目统一的 `resolve_user_scope(user)` 机制过滤查询集（与 `DataScopeMixin.get_scoped_queryset` 同源），MUST NOT 使用手写的、基于角色的硬编码作用域（如"admin/manager 看全部、supervisor 看本大区"）。报表对所有已认证用户可访问（这是既有产品语义），但可见数据 MUST 按其管理授权范围隔离：admin 或持有「全部数据」授权返回全集；其余按 `ManagementScope` 授权的分公司集合过滤；无授权的非 admin 返回空集。

#### Scenario: 无管理授权的 manager 访问报表

- **WHEN** 一个 `manager` 角色用户在 `ManagementScope` 授权表中没有任何记录，请求资产价值报表
- **THEN** 接口返回 200，但结果集为空，MUST NOT 返回全公司数据

#### Scenario: 按大区授权的 supervisor

- **WHEN** 一个 `supervisor` 被授权管理"华东大区"，请求调拨流水报表
- **THEN** 接口返回 200，结果集仅包含"华东大区"下属分公司的调拨记录

#### Scenario: 普通员工只看本公司

- **WHEN** 一个 `staff` 仅归属某分公司，请求按分公司统计报表
- **THEN** 接口返回 200，结果集仅包含其所属分公司的资产，MUST NOT 出现其他分公司

### Requirement: 报表作用域覆盖全部已定义角色

报表的数据范围规则 SHALL 对 `core.permissions.ROLE_LEVELS` 中定义的每一个角色（含 `director`）给出一致处理（统一走 `resolve_user_scope`），MUST NOT 出现某个已定义角色在报表中被静默忽略或被错误降级的情况。

#### Scenario: director 角色的数据范围

- **WHEN** 一个 `director`（level 2）用户请求报表，且其在授权表中有对应大区/分公司授权
- **THEN** 报表按其 `ManagementScope` 授权范围返回数据，与其角色等级一致，MUST NOT 被当作无授权的普通 staff 处理
