## ADDED Requirements

### Requirement: Token 有效期为 7 天
系统 SHALL 为每次登录签发的 Token 设置自创建时刻起 **7 天** 的有效期（`expires_at = created_at + 7 days`），由 `TOKEN_EXPIRATION_DAYS` 统一控制。

#### Scenario: 新登录签发的 Token 有效期为 7 天
- **WHEN** 用户成功登录并获得新 Token
- **THEN** 该 Token 的 `expires_at` 等于创建时间 + 7 天

#### Scenario: 超过 7 天的 Token 被拒绝
- **WHEN** 携带一个创建已超过 7 天的 Token 发起需认证请求
- **THEN** 系统返回 401 且不暴露业务数据

### Requirement: 有效期固定、不随使用延长
系统 SHALL 在 Token 有效期内**不因请求活动而延长**其 `expires_at`（无滑动续期）。

#### Scenario: 持续使用不延长有效期
- **WHEN** 一个未过期 Token 在有效期内被多次用于请求
- **THEN** 其 `expires_at` 保持为创建时设定的值不变

### Requirement: 单账号仅允许单个有效会话
系统 SHALL 保证同一用户在任一时刻只有一个有效会话；该用户每次成功登录 SHALL 使其此前持有的所有 Token **立即失效**，无论它们是否尚未过期。

#### Scenario: 新登录使旧会话立即失效
- **WHEN** 用户已在设备 A 登录获得 Token T1，随后同一用户在设备 B 成功登录获得 Token T2
- **THEN** 用 T1 发起的下一次请求被拒绝（401），用 T2 发起的请求成功

#### Scenario: 被踢会话无需等待过期
- **WHEN** 旧 Token T1 原本尚未到期，但其用户已在别处重新登录
- **THEN** T1 立即失效（而非等到其自身 `expires_at`）

### Requirement: 失效会话触发前端登出
前端 SHALL 在任一需认证请求因 Token 失效（过期或被他处登录踢出）收到 401 时，清除本地保存的 Token 并引导用户回到登录页。

#### Scenario: 被踢设备重定向到登录
- **WHEN** 设备持有的 Token 因该账号在他处登录而失效，设备发起下一次 API 请求
- **THEN** 前端清除 `localStorage` 中的 Token 并跳转至登录页
