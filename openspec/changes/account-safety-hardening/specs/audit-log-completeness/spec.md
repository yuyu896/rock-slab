## ADDED Requirements

### Requirement: 审计成功判定与 HTTP 语义一致

`@audit_log` 的 is_success MUST 反映操作的实际结果：视图正常返回但 HTTP 状态码 ≥ 400（校验失败、权限不足等业务拒绝）时 MUST 记为失败（is_success=False），仅 2xx 响应与无异常返回记成功。异常传播路径的既有记失败行为维持。

#### Scenario: 改密失败记为失败

- **WHEN** 用户提交错误旧密码修改密码（视图返回 400）
- **THEN** 审计日志 is_success=false（不再误记成功）

#### Scenario: 正常操作仍记成功

- **WHEN** 视图返回 200/201
- **THEN** 审计日志 is_success=true
