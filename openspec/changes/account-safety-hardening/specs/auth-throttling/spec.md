## ADDED Requirements

### Requirement: 登录失败计数必须原子

登录失败计数 MUST 以缓存原子自增实现（incr + 首次初始化），MUST NOT 采用「读取-计算-写回」的非原子模式（并发请求可少计绕过锁定阈值）。达到阈值锁定、成功清零、cache 故障 fail-open 的既有语义维持。

#### Scenario: 并发失败全部计数

- **WHEN** 同一手机号近乎同时发生多次失败登录
- **THEN** 每次失败都被计入同一计数（无丢失），达阈值即锁定
