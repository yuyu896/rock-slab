## MODIFIED Requirements

### Requirement: 新建用户不得使用默认弱口令

（2026-09-30 产品裁决对齐）`UserSerializer.create` 在未提供密码时按 `initial-password-policy` 回退 `'123456'` 兜底（分公司行政建号流程依赖），本条款不再要求 password 必填。**显式提供 password 时 MUST 调用 `django.contrib.auth.password_validation.validate_password`，弱口令 MUST 被拒绝**（400 且不创建账号）。

#### Scenario: 建号未提供密码走兜底

- **WHEN** 管理员 `POST /api/users/` 未提交 `password`
- **THEN** 按 `initial-password-policy` 以默认 `123456` 建号（201）

#### Scenario: 建号弱口令被密码校验器拒绝

- **WHEN** 管理员建号时提交不满足强度策略的 `password`（如短于最小长度、纯数字）
- **THEN** 系统返回 400 且不创建账号，错误信息挂在 `password` 字段
