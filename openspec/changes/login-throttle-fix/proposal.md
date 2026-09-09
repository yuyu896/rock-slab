# 登录限流修复——生产共享桶矫正 + 额度放宽到"正常使用永不触发"

## Why

线上实测（2026-09-09）：从公网连打登录接口，第 1 次请求即 429；Redis 中登录限流桶 key 为 `throttle_login_172.18.0.8`——`172.18.0.8` 是 root-nginx 容器内网 IP，**全站所有用户共享同一个登录限流桶（5 次/分钟）**。

根因：生产为两层代理（root-nginx-1:443 → rock-slab-nginx:8080 → Gunicorn），两层都执行 `proxy_add_x_forwarded_for`，到达后端时 `X-Forwarded-For = 真实IP, 172.18.0.8`；而 `NUM_PROXIES` 未在线上配置，默认 1 使 DRF 取 XFF **最后一个**地址 = 容器 IP。后果：

1. **误伤**：134 个账号共享 5 次登录/分钟，早高峰第 6 人起 429；
2. **DoS 向量**：任何扫描器以 5 次/分钟节奏打错误登录，即可让全站登录持续 429（测试时桶正处于被打满状态，已有外部流量在打）。

分桶修复后仍有误伤面：同一办公室出口 IP 的多人共享 5 次/分钟。用户拍板"不限流"（用户 100 余人，限流阻碍正常使用），额度按"正常使用永不触发"重新标定。

## What Changes

- 生产 `NUM_PROXIES=2`（服务器 `.env` 已写入并重建容器验证；`production.py` 固化默认 2 兜底，防 `.env` 丢失退化）
- 登录限流 `5/minute` → `120/minute`（单 IP 标定：全员同一分钟集中登录也够，只挡机器行速爆破；按账号 10 次失败锁 15 分钟保持，作为暴力破解真正防线）
- 用户级限流 `1000/hour` → `10000/hour`（盘点等高频会话不设阻）
- 测试收紧：`test_login_inactive_user` 不再容忍 429 串扰

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `auth-throttling`: NUM_PROXIES 要求补充生产两层链路场景与 production.py 固化；新增"限流额度不误伤正常使用"要求（额度标定 + 同出口多人场景）

## Impact

- **后端**: `rock_slab/settings/base.py`（额度）、`rock_slab/settings/production.py`（NUM_PROXIES 固化）、`apps/authentication/throttling.py`（docstring）、`tests/test_auth.py`
- **运维**: 服务器 `/root/rock-slab/.env` 已加 `NUM_PROXIES=2`（备份 `.env.bak-numproxies-20260909`）
- 前端、API 契约、数据不动；账号锁定策略不动
