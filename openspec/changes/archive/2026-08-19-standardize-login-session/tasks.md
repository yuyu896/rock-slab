## 1. 后端：缩短登录有效期

- [x] 1.1 将 `backend/rock_slab/settings/base.py` 中 `TOKEN_EXPIRATION_DAYS` 由 `30` 改为 `7`（确认 dev/production 未覆盖此值）
- [x] 1.2 确认无需数据库迁移：`ExpiringToken.expires_at` 字段不变，仅新创建的 Token 按 7 天生成

## 2. 后端：登录即轮换（单会话强制）

- [x] 2.1 重构 `backend/apps/authentication/views.py` 的 token 签发逻辑：每次登录都**删除该用户全部 Token**（`ExpiringToken` + `BaseToken`）后创建新 Token，不再「未过期即复用」；保留现有 `IntegrityError` 兜底（函数更名为 `issue_login_token`）
- [x] 2.2 更新该函数 docstring/命名以反映「登录即轮换、单会话」语义
- [x] 2.3 检查并更新依赖「复用旧 Token」语义的既有测试（已确认无测试依赖旧语义）

## 3. 前端：失效会话处理

- [x] 3.1 核对 `frontend/src/utils/request.ts` 的 401 响应拦截器：确认「Token 不存在（被他处登录踢出）」返回的 401 同样触发清除 `localStorage` Token 并跳转 `/login`（现有逻辑已覆盖，无需改动）
- [ ] 3.2 （可选）登录页补充通用「登录已失效，请重新登录」提示文案

## 4. 测试

- [x] 4.1 新增后端用例：新登录签发 Token 的 `expires_at` = 创建时间 + 7 天
- [x] 4.2 新增后端用例：Token 在有效期内被多次使用后 `expires_at` 不变（固定不续期）
- [x] 4.3 新增后端用例：同一用户新登录后，旧 Token 立即失效（携带旧 Token 请求返回 401），新 Token 正常
- [x] 4.4 运行 `pytest` 确认后端全绿（340 passed, 6 xfailed）

## 5. 验证与收尾

- [ ] 5.1 本地手动验证：同账号两处登录互踢、7 天过期返回 401、前端正确跳转登录
- [x] 5.2 运维裁定：上线时**清理存量 Token**（强制全员按新规则重登）——已决定执行
