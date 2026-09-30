## MODIFIED Requirements

### Requirement: 建号默认初始密码 123456

`UserSerializer.create` MUST 在未提供 password 时回退到默认 `'123456'`（兜底路径不做强度校验）。**显式提供 password 时，MUST 调用 `django.contrib.auth.password_validation.validate_password(value, 瞬时User(phone,name))`，不通过 MUST 返回 400 且不创建账号**（错误信息挂在 `password` 字段）。员工首次登录后可通过 `/api/auth/password/` 自行修改密码。

> 2026-09-30 产品裁决：保留 123456 兜底（分公司行政建号流程不动），显式密码一律过强度校验。本 requirement 与 `password-security` / `account-lifecycle-security` 的默认口令条款已按此口径对齐（默认口令策略归本规范；显式密码强度归 AUTH_PASSWORD_VALIDATORS），规范冲突消除。

#### Scenario: 建号未传密码用默认 123456

- **WHEN** 管理员 `POST /api/users/` 未提交 password
- **THEN** 账号创建成功（201），初始密码为 `123456`（`user.check_password('123456')` 为真）

#### Scenario: 建号显式弱口令被密码校验器拒绝

- **WHEN** 管理员建号时提交不满足强度策略的 password（短于最小长度 / 纯数字 / 与手机号或姓名相似）
- **THEN** 系统返回 400 且不创建账号，错误信息挂在 `password` 字段

#### Scenario: 建号显式强口令正常生效

- **WHEN** 管理员建号时提交满足强度策略的 password
- **THEN** 账号创建成功（201），密码为提交值

#### Scenario: 前端建号表单不要求填密码

- **WHEN** 管理员在前端建号表单提交新用户
- **THEN** 表单无密码输入框，提交 payload 不含 password 字段，后端用默认 123456 建号
