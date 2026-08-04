# account-lifecycle-security Specification

## Purpose
TBD - created by archiving change audit-findings-remediation. Update Purpose after archive.
## Requirements
### Requirement: 用户更新不得绕过密码哈希

`UserSerializer` 的更新路径 MUST NOT 将 `password` 字段原样写入数据库。`password` MUST 为 create-only（更新时从可写字段中排除）；若更新路径仍收到 password，MUST 经 `set_password()` 处理。密码变更 MUST 经 `/api/auth/password/` 接口（校验旧密码 + `validate_password` + 轮换 Token）。

#### Scenario: 通过更新接口注入预生成哈希无法接管账号
- **WHEN** 持 `manage_users` 授权的用户 `PATCH /api/users/{victim_id}/` 提交一个本地预生成的有效密码哈希作为 `password`
- **THEN** 该哈希不被原样写入受害者 password 列；随后用对应明文 `POST /api/auth/login/` 登录失败，账号未被接管

#### Scenario: 更新接口不接受 password 字段
- **WHEN** 任意用户 `PATCH /api/users/{id}/` 同时提交 `name` 与 `password`
- **THEN** `name` 正常更新，`password` 被忽略（或该字段在更新序列化器中不存在）

### Requirement: 停用账号必须立即失效其 Token

将用户 `status` 置为 `inactive` 时 MUST 同步 `is_active=False` 并删除其全部 `ExpiringToken`；`ExpiringTokenAuthentication` MUST 拒绝已停用账号的任何 token（无论是否过期）。

#### Scenario: 离职停用后旧 Token 立即失效
- **WHEN** 管理员把某用户 `status` 改为 `inactive`
- **THEN** 该用户此前签发的所有 token 在下一次 API 调用时返回 401，不得等到自然过期

### Requirement: 新建用户不得使用默认弱口令

`UserSerializer.create` MUST NOT 回退到硬编码默认密码（`'123456'`）。`password` 为必填，未提供时 MUST 返回 400 且不创建账号；创建路径 MUST 调用 `django.contrib.auth.password_validation.validate_password`，弱口令 MUST 被拒绝。

#### Scenario: 建号未提供密码被拒
- **WHEN** 管理员 `POST /api/users/` 未提交 `password`
- **THEN** 系统返回 400 且不创建账号

#### Scenario: 建号弱口令被密码校验器拒绝
- **WHEN** 管理员建号时提交不满足强度策略的 `password`（如短于最小长度）
- **THEN** 系统返回 400 并给出校验错误，不创建账号

