## Why

账号与审计侧五个小缺口（审计/复现确认）：① 头像上传与删除共用 url_path='avatar'，DRF 路由按方法名排序先注册遮蔽后者 → POST 恒 405（5 个 xfail 测试存档）；② 建号手机号显式 validators 覆盖了自动 UniqueValidator → 撞号直达 IntegrityError 500（xfail 存档）；③ 登录失败计数 get+set 非原子，并发请求可少计绕过锁定阈值；④ `@audit_log` 的 is_success 仅在异常传播时置 False，正常返回的 4xx Response 仍记成功（改密失败 400 记成功）；⑤ `/api/health/` 异常时把数据库异常原文（`str(e)`）下发给未鉴权调用方。

## What Changes

- 头像 upload/delete 合并为单 action 按 `request.method` 分流（照 assets image action 的既有先例，POST 405 根治，xfail 转正）
- phone 字段在保留格式校验的同时加回 `UniqueValidator`（撞号 400 带明确提示，xfail 转正）
- 登录失败计数改 `cache.incr`（不存在时初始化 1）——计数原子化；语义从滑动窗变固定窗（自首次失败起 5 分钟），在模块注释记录
- `@audit_log` 全局语义修正：返回 DRF Response 且 `status_code >= 400` 时 `is_success=False`——审计的"成功"与 HTTP 语义对齐
- health 异常分支不再下发异常原文：固定 `{'status': 'error'}`（503），细节进服务端日志；免鉴权维持（容器健康检查依赖）
- SECURE_SSL_REDIRECT 维持「外层 nginx 统一处理」的既有设计，不改代码（规范记录口径）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `avatar-system`: 头像上载/删除路由要求（单 action 分流）
- `personnel-management`: 创建用户手机号唯一校验要求
- `auth-throttling`: 失败计数原子性要求
- `audit-log-completeness`: is_success 语义（4xx=失败）
- `production-config`: health 端点不泄露异常细节

## Impact

- `backend/apps/users/views.py`（头像合并）、`serializers.py`（UniqueValidator）
- `backend/apps/authentication/account_lockout.py`（incr）
- `backend/apps/audit/decorators.py`（is_success）
- `backend/rock_slab/urls.py`（health）
- 测试：两个 xfail 转正、新增计数原子/is_success/health 用例；全量回归
- 无迁移；`change_password` 失败审计从成功变失败（行为修正）
