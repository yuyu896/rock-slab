## MODIFIED Requirements

### Requirement: 禁止默认弱口令

默认口令策略由 `initial-password-policy` 规定（2026-09-30 产品裁决：`UserSerializer.create` 在未提供密码时回退 `'123456'` 兜底，本条款不再禁止该兜底）。本规范约束**显式提供**的密码：建号（`POST /api/users/` 的 `password`）与改密（`/api/auth/password/`）MUST 通过 `AUTH_PASSWORD_VALIDATORS` 校验（`validate_password(value, user)`），不通过 MUST 返回 400 并附校验错误信息，且 MUST NOT 创建账号/修改密码。

#### Scenario: 建号显式密码不满足强度

- **WHEN** 管理员建号时提交不满足强度策略的 password（如短于最小长度、纯数字）
- **THEN** 系统返回 400 与校验错误，不创建账号

#### Scenario: 建号未传密码走兜底

- **WHEN** 管理员创建用户但请求体中未包含 `password`
- **THEN** 按 `initial-password-policy` 以默认 `123456` 建号（201），不因缺密码而拒绝

#### Scenario: 改密新密码不满足强度

- **WHEN** 已认证用户提交修改密码，新密码不满足配置的最小长度/复杂度
- **THEN** 系统返回 400 与校验错误，旧密码保持不变
