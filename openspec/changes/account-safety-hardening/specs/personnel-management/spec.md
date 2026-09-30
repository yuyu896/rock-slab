## ADDED Requirements

### Requirement: 创建用户手机号唯一校验

创建用户（POST /api/users/）的手机号 MUST 经唯一性校验：手机号已被占用 MUST 返回 400（提示手机号已存在），MUST NOT 直达数据库完整性错误（500）。格式校验（11 位数字）维持不变。

#### Scenario: 重复手机号建号被拒

- **WHEN** 管理员以已占用手机号创建用户
- **THEN** 返回 400（错误挂在 phone 字段），无账号创建、无 500
