## ADDED Requirements

### Requirement: 禁止默认弱口令

创建用户时系统 MUST NOT 使用任何固定的默认密码（如 `'123456'`）。当请求未提供密码时，系统 SHALL 拒绝创建，或 SHALL 生成一个随机密码并通过安全渠道交付（并标记需在首次登录时修改）。`UserSerializer` 的 `password` 字段 MUST NOT 带有默认值。

#### Scenario: 新建用户未传密码

- **WHEN** 管理员创建用户但请求体中未包含 `password`
- **THEN** 系统不创建使用 `'123456'` 的账号；要么返回 400 要求提供密码，要么生成随机密码并要求首登改密

### Requirement: 超管凭据必须显式提供

`create_superuser` 管理命令 MUST NOT 为 `--password` 提供任何默认值（不得默认 `admin123`）。密码 SHALL 通过命令行参数或环境变量显式提供；未提供时命令 SHALL 以非零状态码退出并提示。手机号同样 SHALL 显式提供。

#### Scenario: 不带参数创建超管

- **WHEN** 运行 `python manage.py create_superuser` 且未提供 `--password` 与环境变量
- **THEN** 命令打印错误并以非零状态码退出，MUST NOT 创建一个密码为 `admin123` 的全权管理员

### Requirement: 修改密码必须通过 Django 密码校验器

`change_password` 接口在设置新密码前 SHALL 调用 `django.contrib.auth.password_validation.validate_password(new_password, user=user)`。校验不通过时 MUST 返回 400 并附校验错误信息，且 MUST NOT 修改密码。

#### Scenario: 新密码不满足强度

- **WHEN** 已认证用户提交修改密码，新密码 `new` 不满足配置的最小长度/复杂度
- **THEN** 系统返回 400 与校验错误，旧密码保持不变

#### Scenario: 新密码满足强度且旧密码正确

- **WHEN** 已认证用户提交正确的旧密码和满足强度的新密码（通过 `application/json` 请求体，字段为 `oldPassword/newPassword`）
- **THEN** 系统更新密码、轮换 Token，返回 200 与新 Token
