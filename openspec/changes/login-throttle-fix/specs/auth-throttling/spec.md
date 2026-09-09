# auth-throttling 增量

## MODIFIED Requirements

### Requirement: 登录限流按真实客户端 IP 生效

当应用部署在反向代理（Nginx）之后时，DRF 的 `NUM_PROXIES` SHALL 配置为代理层数，使 `LoginRateThrottle.get_ident` 取信 `X-Forwarded-For` 中的真实客户端 IP（倒数第 N 个地址，N=受信代理层数），而非所有请求共享的容器内部地址。MUST NOT 出现"全体用户共用同一限流桶"的情况。生产两层链路（root-nginx → rock-slab-nginx → Gunicorn）SHALL 取值 2，并在 `production.py` 固化为默认值（环境变量可覆盖）；开发单层代理取值 1。

#### Scenario: 不同客户端 IP 各自计数

- **WHEN** 两个不同公网 IP 各自发起多次登录请求
- **THEN** 两个 IP 的失败次数分别独立计数，一个 IP 触发限流不影响另一个 IP

#### Scenario: 生产两层链路取真实 IP

- **WHEN** 生产环境（root-nginx 与 rock-slab-nginx 两层均追加 X-Forwarded-For）用户从公网发起登录
- **THEN** 限流桶按该用户的公网 IP 计数，而非任一层代理的容器 IP

#### Scenario: 生产配置防退化

- **WHEN** 生产容器重建且 `.env` 缺失 `NUM_PROXIES` 项
- **THEN** `production.py` 默认值 2 生效，不回退到全站共享桶

## ADDED Requirements

### Requirement: 限流额度不误伤正常使用

限流额度 SHALL 按"全量用户正常使用永不触发"标定：登录限流 SHALL 不低于 120 次/分钟/客户端 IP（同一出口 IP 的全员集中登录不触发）；登录后接口的用户级额度 SHALL 不低于 10000 次/小时（盘点等高频会话不设阻）。额度调整 MUST NOT 移除按账号失败锁定（单账号暴力破解防线保持）。

#### Scenario: 同一出口 IP 多人集中登录

- **WHEN** 同一办公室出口 IP 下数十名用户在同一分钟内先后登录成功
- **THEN** 所有登录均正常处理，无人收到 429

#### Scenario: 机器行速爆破仍被拦

- **WHEN** 单个 IP 以远超人类操作的行速（如每秒数次）连续提交登录
- **THEN** 超出 120 次/分钟/IP 额度后返回 429，密码校验不再执行

#### Scenario: 高频业务会话不受阻

- **WHEN** 单个用户在盘点高峰持续提交扫码结果与列表刷新（分钟级十余次请求）
- **THEN** 全程不触发用户级限流（10000 次/小时额度不可达）
