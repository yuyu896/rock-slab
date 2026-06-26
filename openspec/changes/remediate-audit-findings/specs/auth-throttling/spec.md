## ADDED Requirements

### Requirement: 登录限流按真实客户端 IP 生效

当应用部署在反向代理（Nginx）之后时，DRF 的 `NUM_PROXIES` SHALL 配置为代理层数（单层 Nginx 为 `1`），使 `LoginRateThrottle.get_ident` 取信 `X-Forwarded-For` 中的真实客户端 IP，而非所有请求共享的容器内部地址。MUST NOT 出现"全体用户共用同一限流桶"的情况。

#### Scenario: 不同客户端 IP 各自计数

- **WHEN** 两个不同公网 IP 各自发起多次登录请求
- **THEN** 两个 IP 的失败次数分别独立计数，一个 IP 触发限流不影响另一个 IP

### Requirement: 单账号暴力破解锁定

登录失败时系统 SHALL 按手机号维度累计失败次数。同一手机号在配置窗口内（如 5 分钟内 10 次）连续失败后，该账号 SHALL 被临时锁定一段时间（如 15 分钟），锁定期间即使密码正确也 SHALL 返回锁定提示。成功登录 SHALL 清零失败计数。

#### Scenario: 同一手机号反复失败

- **WHEN** 同一手机号在窗口内连续登录失败达到阈值
- **THEN** 该账号被临时锁定，后续登录（即使凭据正确）返回账号锁定提示

#### Scenario: 锁定后等待解锁

- **WHEN** 账号处于锁定窗口内，攻击者提交正确密码
- **THEN** 系统返回锁定提示并拒绝登录；窗口结束后正确密码可正常登录

#### Scenario: 成功登录清零计数

- **WHEN** 一个曾失败若干次的账号随后用正确密码登录成功
- **THEN** 其失败计数被清零，不进入锁定
