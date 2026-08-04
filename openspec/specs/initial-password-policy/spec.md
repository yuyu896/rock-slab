# initial-password-policy Specification

## Purpose
TBD - created by archiving change restore-default-initial-password. Update Purpose after archive.
## Requirements
### Requirement: 建号默认初始密码 123456

`UserSerializer.create` MUST 在未提供 password 时回退到默认 `'123456'`。建号 MUST NOT 因未传 password 或密码强度不足而失败（接受 `123456` 等弱口令作为初始密码）。员工首次登录后可通过 `/api/auth/password/` 自行修改密码。

> ⚠️ 本 requirement 为**临时策略**，接受弱口令风险（详见 proposal「已知风险」）。后续提案将引入「随机初始密码 + 首登强制改密」替换之。本 requirement 与 `audit-findings-remediation` 的 `account-lifecycle-security` R3「新建用户不得使用默认弱口令」冲突，归档时协调。

#### Scenario: 建号未传密码用默认 123456

- **WHEN** 管理员 `POST /api/users/` 未提交 password
- **THEN** 账号创建成功（201），初始密码为 `123456`（`user.check_password('123456')` 为真）

#### Scenario: 建号接受弱口令作为初始密码

- **WHEN** 管理员建号时提交弱口令（如短于最小长度）
- **THEN** 账号创建成功（201），密码为提交值（不因强度校验拒绝）

#### Scenario: 前端建号表单不要求填密码

- **WHEN** 管理员在前端建号表单提交新用户
- **THEN** 表单无密码输入框，提交 payload 不含 password 字段，后端用默认 123456 建号

