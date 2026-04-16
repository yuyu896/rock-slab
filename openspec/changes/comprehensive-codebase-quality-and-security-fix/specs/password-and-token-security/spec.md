## ADDED Requirements

### Requirement: 密码复杂度验证
系统 SHALL 在用户修改密码和创建用户时强制执行密码复杂度规则：长度至少 6 位。

#### Scenario: 修改密码时验证复杂度
- **WHEN** 用户通过 `/api/auth/password/` 提交新密码且密码长度小于 6 位
- **THEN** 系统 SHALL 返回 400 错误，提示密码不符合复杂度要求

#### Scenario: 创建用户时验证密码
- **WHEN** 管理员通过 `/api/users/` 创建新用户时提供短于 6 位的密码
- **THEN** 系统 SHALL 拒绝创建并返回验证错误

### Requirement: Token 过期机制
系统 SHALL 为每个认证 Token 设置过期时间。Token 默认有效期 MUST 为 30 天。过期的 Token SHALL 被拒绝认证。

#### Scenario: 正常 Token 认证
- **WHEN** 用户携带未过期的 Token 请求 API
- **THEN** 系统 SHALL 正常处理请求

#### Scenario: 过期 Token 认证
- **WHEN** 用户携带已过期的 Token 请求 API
- **THEN** 系统 SHALL 返回 401 Unauthorized，前端 SHALL 引导用户重新登录

#### Scenario: 登录时签发新 Token
- **WHEN** 用户成功登录
- **THEN** 系统 SHALL 创建一个 expires_at 为 30 天后的 Token 并返回

### Requirement: 修改密码后轮换 Token
系统 SHALL 在用户修改密码后立即使其当前 Token 失效，并签发新 Token。

#### Scenario: 修改密码后旧 Token 失效
- **WHEN** 用户成功修改密码
- **THEN** 系统 SHALL 删除旧 Token，创建新 Token 并返回给客户端

#### Scenario: 修改密码后使用旧 Token
- **WHEN** 用户修改密码后使用旧 Token 请求 API
- **THEN** 系统 SHALL 返回 401 Unauthorized

### Requirement: LoginSerializer 用于登录验证
登录视图 MUST 使用 `LoginSerializer` 进行输入验证，而非直接从 `request.data` 读取。

#### Scenario: 登录使用序列化器验证
- **WHEN** 用户提交登录请求（POST `/api/auth/login/`）
- **THEN** 系统 SHALL 通过 `LoginSerializer` 验证 phone 和 password 字段，验证失败返回标准 DRF 错误格式
