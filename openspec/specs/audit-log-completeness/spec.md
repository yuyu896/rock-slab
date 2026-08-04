# audit-log-completeness Specification

## Purpose
TBD - created by archiving change audit-findings-remediation. Update Purpose after archive.
## Requirements
### Requirement: 审计装饰器必须兼容函数视图与 ViewSet

`audit_log` 装饰器 MUST 正确从函数视图（`@api_view`，`args[0]` 为 request）与 ViewSet 方法（`args[0]` 为 self，request 取自 `self.request`）两种调用形态中取得 request 与当前用户，并写入审计记录。关键敏感操作（改密、用户增删改、审批）MUST 产生审计日志，不得因视图形态不同而静默漏审。

#### Scenario: 修改密码被写入审计日志
- **WHEN** 任意已登录用户成功调用 `PUT /api/auth/password` 修改密码
- **THEN** 审计日志中存在一条 `action=change_password` 记录，包含操作人、时间与资源类型

#### Scenario: 函数视图与 ViewSet 审计行为一致
- **WHEN** 对一个函数视图与一个等价 ViewSet action 分别应用 `@audit_log`
- **THEN** 二者触发时均成功写入审计记录，request/user 解析均不为 None

