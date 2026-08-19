## Context

磐盘使用自定义 `ExpiringToken`（多表继承自 DRF `Token`）做 Token 认证：

- 有效期由 `rock_slab/settings/base.py` 的 `TOKEN_EXPIRATION_DAYS`（当前 **30**）控制，Token 创建时一次性写入 `expires_at`。
- `ExpiringTokenAuthentication.authenticate_credentials` 在每次请求时检查 `is_expired`，过期则返回 401——即「固定有效期、无滑动续期」语义**已经存在**。
- DRF `Token` 对 `user` 有唯一约束（每用户一份）。`get_or_create_token` 在 Token 未过期时**复用**旧 Token，于是第二台设备登录后与第一台拿到同一 key、可并发使用——这就是「多端同时在线」的根因。

约束：生产已上线（qhpanpan.top），需平滑过渡；不引入新的外部依赖；尽量复用既有模型与认证类。

## Goals / Non-Goals

**Goals:**
- 将登录有效期由 30 天缩短为 **7 天**，固定到期、不随使用延长。
- 强制**单会话**：同一账号新登录使此前所有会话立即失效。

**Non-Goals:**
- 不引入「记住我 / 记住此设备」等可配置有效期。
- 不做滑动续期。
- 不做多会话上限（如允许 2 台）——明确只要单会话。
- 不为「被踢」提供独立于「过期」的专属提示文案（见 Open Questions）。

## Decisions

### 决策 1：有效期 = 7 天，固定不续期
- **做法**：`TOKEN_EXPIRATION_DAYS = 7`（仅改 `base.py` 一处，dev/prod 继承）。`is_expired` 逻辑已存在，无需改认证类。
- **理由**：用户策略裁定；固定有效期行为可预期、最便于统一管控。
- **备选**：滑动续期（每次请求重置 `expires_at`）——被否，管控偏弱；更短时长（8h/24h）——用户选择 7 天。

### 决策 2：单会话 = 登录即轮换 Token
- **做法**：把 `get_or_create_token` 改为**每次成功登录都删除该用户全部 Token（子表 + 基础表）再创建全新 Token**，不再「未过期即复用」。保留现有 `IntegrityError` 兜底（并发登录自愈）。
- **效果**：旧设备持有的 Token 被删除 → 其下次请求查无此 key → `ExpiringTokenAuthentication` 返回 401「无效的认证令牌」→ 前端拦截器清 Token、跳登录。新设备拿到新 Token 正常使用。
- **理由**：复用既有「每用户一份 Token」模型，改动面最小、语义清晰。
- **备选**：
  - 在 `User` 上加 `session_generation` 计数、Token 记录所属代次，旧代次 Token 被拒并返回「已在别处登录」——更利于提示文案，但新增字段+迁移+认证类改动，超出当前规范目的，**暂不做**。
  - 允许多 Token + N 端上限——与「单会话」诉求矛盾，否。

### 决策 3：被踢设备的提示按「登录已失效」统一处理
- **做法**：复用前端 `utils/request.ts` 现有 401 拦截（清 Token + 跳 `/login`）。被踢与过期都走同一跳转路径。
- **理由**：区分「被踢」需决策 2 的备选代次机制；当前优先规范行为，提示文案差异化列为 Open Question。

## Risks / Trade-offs

- **[每次登录轮换]** 同一用户高频/并发登录可能撞 `IntegrityError` → **缓解**：`get_or_create_token` 已有 try/except 兜底（撞则 get 现有），保留。
- **[被踢用户无专属提示]** 用户被另一端踢下线时只看到跳转登录，可能困惑 → **缓解**：登录页可加通用「登录已失效，请重新登录」提示；专属文案见 Open Question。
- **[7 天vs 30 天体验下降]** 习惯长期登录的用户需更频繁重登 → **接受**，这正是规范目的。
- **[存量 Token 仍按 30 天衰减]** 上线后已签发的 Token 不会立刻变成 7 天 → **缓解**：见 Migration Plan，可选清理。

## Migration Plan

1. 后端改动：`base.py` 改 `TOKEN_EXPIRATION_DAYS = 7`；`get_or_create_token` 改为登录即轮换。**无需数据库迁移**（`expires_at` 字段不变，新 Token 按新设置生成）。
2. 前端：确认 `request.ts` 的 401 拦截覆盖「被踢（Token 不存在）」路径；如需统一提示文案则小改登录页。
3. 部署：标准 `deploy.sh`，无破坏性基础设施变更。
4. 存量 Token：默认让其按各自原始有效期自然衰减（渐进生效）。**可选**：上线时跑一次 Token 清理（强制全员重登）以立即全量生效——由运维决定。

## Open Questions

1. 是否需要为「被另一设备踢下线」提供区别于「过期」的专属提示？当前默认**不做**，待后续按需启用代次机制。
2. 上线时是否清理存量 Token 强制立即生效？当前默认**不清**，交运维裁定。
