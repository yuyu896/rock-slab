# 登录限流修复 — 实施任务

## 1. 生产共享桶矫正

- [x] 1.1 服务器 `.env` 写入 `NUM_PROXIES=2`（备份 `.env.bak-numproxies-20260909`），`docker compose up -d backend` 重建容器
- [x] 1.2 公网实测分桶：6 连打登录前 5 次 401、第 6 次 429；Redis 桶 key 变为本机公网 IP，多个外部 IP 桶并存互不影响
- [x] 1.3 `production.py` 固化 `REST_FRAMEWORK['NUM_PROXIES']` 默认 2（`.env` 缺项时不退化）

## 2. 额度放宽

- [x] 2.1 `base.py`：`login` 5/minute → 120/minute；`user` 1000/hour → 10000/hour（附标定说明注释）
- [x] 2.2 `throttling.py` docstring 同步；`test_auth.py` 移除 429 容忍断言（收紧为仅 403）

## 3. 测试与验证

- [x] 3.1 `pytest tests/test_auth.py` 全绿（限流/锁定/会话策略无回归）
- [x] 3.2 后端全量 pytest 通过
- [x] 3.3 部署后线上复验：公网连打登录 10 次不触发 429（120/min 额度内），登录功能正常
