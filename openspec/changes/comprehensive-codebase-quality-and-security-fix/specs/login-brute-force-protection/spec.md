## ADDED Requirements

### Requirement: 登录端点独立限流
系统 SHALL 对 `/api/auth/login/` 端点实施独立的速率限制，每个 IP 每分钟最多 5 次登录尝试。

#### Scenario: 正常频率登录
- **WHEN** 同一 IP 在 1 分钟内发送 3 次登录请求
- **THEN** 系统 SHALL 正常处理所有请求

#### Scenario: 超出登录频率限制
- **WHEN** 同一 IP 在 1 分钟内发送第 6 次登录请求
- **THEN** 系统 SHALL 返回 429 Too Many Requests，响应体包含限流提示信息

#### Scenario: 限流窗口自动恢复
- **WHEN** 被 429 限流的 IP 等待 1 分钟后再次尝试登录
- **THEN** 系统 SHALL 正常处理该登录请求
