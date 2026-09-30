## ADDED Requirements

### Requirement: Role-line guard on user update and delete

用户更新（PUT/PATCH `/api/users/<id>`）与删除（DELETE `/api/users/<id>`）MUST 校验目标用户的**当前**岗位属于操作者的岗位分配权线（`MANAGEABLE_ROLES`：admin → admin/director/manager/leader，director → manager/leader，manager → manager/leader，leader → 仅本人）。admin 操作者与目标为本人的请求豁免该校验。校验 MUST 先于「全部数据」（scope.all）范围放行执行；不满足时 MUST 返回 400 且不落库、不发删除。该校验同时覆盖：不带 role 字段的越权修改/删除、带 role 字段的降级变更（把高岗位用户改为权线内低岗位）。持「全部数据」授权的操作者对用户的管理范围语义为「权线内的任何用户」。

#### Scenario: Manager with all-data grant cannot modify an admin account
- **WHEN** role=manager 的操作者（持 manage_users + 全部数据范围）PATCH 一个 role=admin 的用户（如仅改 name）
- **THEN** 系统返回 400（提示无权管理该岗位），目标用户不变更

#### Scenario: Manager with all-data grant cannot delete an admin account
- **WHEN** 同上操作者 DELETE 一个 role=admin 的用户
- **THEN** 系统返回 400，目标用户仍存在

#### Scenario: Demotion across the role line is rejected
- **WHEN** role=manager 的操作者 PATCH 一个 role=director 的用户并提交 `role: "leader"`
- **THEN** 系统返回 400，目标用户岗位仍为 director

#### Scenario: Same-line management continues to work
- **WHEN** role=manager 的操作者按既有范围（同分公司或全部数据授权）PATCH/DELETE 权线内的 manager/leader 用户
- **THEN** 请求按既有语义成功（200/204），同岗互管行为不变

#### Scenario: Admin and self are exempt
- **WHEN** admin 操作者更新/删除任意岗位用户，或任意用户更新本人资料
- **THEN** 不受权线校验影响，按既有语义处理

#### Scenario: Branch scope does not widen the role line
- **WHEN** role=manager 的操作者（本分公司范围）PATCH 同分公司内 role=director 的用户
- **THEN** 系统返回 400，数据范围与权线是两道独立的闸
