## Why

当前登录会话缺乏管控：自定义 `ExpiringToken` 有效期长达 30 天，且同一账号可在多台设备同时保持登录——因为 DRF Token 每用户仅一份，`get_or_create_token` 在未过期时会**复用**旧 Token，导致第二台设备登录后与第一台共享同一会话、两端可并发使用。这带来账号共享/盗用风险，也不符合企业资产系统的使用规范。需要缩短有效期并强制单会话，使登录行为可预期、可管控。

## What Changes

- **缩短登录有效期**：`TOKEN_EXPIRATION_DAYS` 由 30 天改为 **7 天**（**BREAKING**——7 天后 Token 失效需重新登录）。
- **固定有效期、不做滑动续期**：维持现有「到期即失效」语义，使用过程不延长会话（Token 创建时一次性确定 `expires_at`）。
- **强制单会话**：同一账号每次成功登录都签发全新 Token，并使该用户此前所有 Token **立即失效**；被踢设备下次请求得到 401、被引导回登录页（**BREAKING**——多端同时在线不再可能）。

## Capabilities

### New Capabilities
- `session-policy`: 登录会话的有效期与并发管控策略——Token 有效期长度、是否滑动续期、单账号并发会话上限与新登录互踢行为。

### Modified Capabilities
<!-- 无：现有 specs 中不含认证/会话相关 capability（login-subtitle 仅涉 UI）。 -->

## Impact

- **后端 `apps/authentication/`**：`get_or_create_token` 改为「登录即轮换」（删除该用户所有旧 Token 再创建新的）；`ExpiringTokenAuthentication` 已具备过期拒绝逻辑，无需改动。
- **后端配置 `rock_slab/settings/base.py`**：`TOKEN_EXPIRATION_DAYS = 7`。
- **前端 `utils/request.ts`**：401 拦截器已会清除 Token 并跳转登录；需确认「被踢」与「过期」两种场景的提示文案与跳转行为一致。
- **运维**：存量 Token 仍按其原始 30 天有效期自然衰减；如需立即全量生效，可选清理全部 Token（强制全员重新登录）。
- **测试**：新增 Token 7 天有效期、固定不续期、单会话互踢三类用例。
