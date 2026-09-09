# design — 登录限流修复

## 根因分析

DRF `BaseThrottle.get_ident` 在 `NUM_PROXIES=N` 时取 `X-Forwarded-For` 倒数第 N 个地址。生产链路：

```
浏览器 ──▶ root-nginx-1(443) ──▶ rock-slab-nginx(8080) ──▶ Gunicorn(8002)
           追加 XFF: 真实IP       追加 XFF: 真实IP, 172.18.0.8
```

两层 nginx 都执行 `proxy_add_x_forwarded_for`，后端收到的 XFF 末位恒为 root-nginx 容器 IP。`NUM_PROXIES` 默认 1 → ident 恒为 `172.18.0.8` → 全站共享一个登录桶（Redis 实测 key `throttle_login_172.18.0.8`，TTL 活跃、桶满导致新请求全 429）。

`X-Real-IP` 同样不可用：rock-slab-nginx 以 `proxy_set_header X-Real-IP $remote_addr` 覆盖为上游容器 IP。

## 方案取舍

| 方案 | 结论 |
|------|------|
| `NUM_PROXIES=2`（.env + production.py 固化） | ✅ 采用。DRF 原生机制，注释本就预留环境变量覆盖口 |
| rock-slab-nginx 透传上层 XFF 不追加 | 否。破坏 XFF 语义，且 nginx conf 不在仓库、易在恢复时丢失（见 nginx-conf-not-in-repo 教训） |
| 完全移除登录限流 | 否。登录走 PBKDF2 校验（~百毫秒级 CPU），2 核机器被行速打登录会拖垮全站——去掉限流反而让"人员无法正常使用"成真。保留 120/min 机器闸门 |
| 只调高到 10-20/min | 否。同办公室出口 IP 数十人集中登录仍可能撞线；直接标定到 120/min 一步到位 |

## 额度标定

- **login 120/min/IP**：134 账号、最大同出口并发登录几十次的量级下不可达；单 IP 机器行速（>2 次/秒持续）必达。单账号爆破由既有 account_lockout（10 次失败/5 分钟锁 15 分钟）防，双层互补。
- **user 10000/hour**：≈166 次/分钟持续不可达；原 1000/hour（≈17 次/分钟）在盘点扫码高频会话存在真实撞线风险。
- **anon 100/hour 不动**：DRF 先权限后限流，未认证请求到保护端点在权限层 401，不计入桶；登录视图自持 throttle_classes，实际作用面为空。

## 实施与验证

1. 服务器 `.env` 加 `NUM_PROXIES=2` → `docker compose up -d backend` 重建（已完成，备份 `.env.bak-numproxies-20260909`）
2. 公网实测：6 连打登录 → 前 5 次 401、第 6 次 429 且桶 key 为本机公网 IP（分桶生效）；Redis 出现多个互不干扰的真实 IP 桶
3. 代码：base.py 额度、production.py 固化 NUM_PROXIES=2、throttling.py 文案、test_auth.py 收紧断言（429 容忍移除）
4. 部署后线上复验：连打登录不触发 429（120/min 内）
