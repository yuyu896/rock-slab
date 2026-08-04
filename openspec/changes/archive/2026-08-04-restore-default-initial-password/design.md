## Context

`audit-findings-remediation`（task 3.2 / 3.3，已上线）移除了建号默认密码 `123456`，改为建号必填密码 + 强度校验 + 前端密码输入框。管理员实际使用中觉得为每个员工设密码繁琐。产品决策：**临时回退**到「建号默认 123456 + 员工自改」，后续系统完善后重新设计安全方案。

磐盘已有完整的改密接口（`/api/auth/password/`，校验旧密码 + 强度 + 轮换 token），员工登录后可自行改密。本次只回退「建号初始密码」这一项，不动其他。

## Goals / Non-Goals

**Goals:**
- 建号恢复默认初始密码 `123456`，管理员无需设密码。
- 前端建号表单去掉密码输入框，简化流程。
- 保留 audit-findings 的其他安全改动（防账号接管、停用失效 token、写越权等）。

**Non-Goals:**
- 不引入随机密码 / 强制首登改密（留待后续提案）。
- 不回退其他 audit-findings 安全修复。
- 不重置存量用户密码（只影响新建账号）。

## Decisions

### D1. 恢复 `UserSerializer.create` 默认 `'123456'`
**选择**：`create` 内 `password = validated_data.pop('password', '123456')`（回到 audit-findings 之前的逻辑）；移除「未传密码报 400」与 `password_validation.validate_password` 调用，接受 `123456` 作为初始密码。
**理由**：建号统一初始密码，管理员一键创建，分发方便。
**备选**：保留必填 + 强度校验（audit-findings 现状）——管理员负担，被否决。

### D2. 去掉前端建号密码输入框
**选择**：`views/Organization.vue` 建号表单移除 password `<input>` 与 ≥8 位必填校验；`addItem` 不预填 password；`createUser` 分支不传 password 字段（后端回退默认 123456）。编辑用户分支本就不传 password，保持不变。
**理由**：建号流程恢复简化（不填密码）。

### D3. 保留其他 audit-findings 安全改动
**不回退**：`UserSerializer.update` 的 password create-only（防账号接管）、停用账号联动失效 token、认证层 status 校验、写越权防护、盘点并发、审计/通知范围等。这些与「初始密码」无关，继续保留。
**理由**：只回退产品要求的初始密码项，不扩大回退范围。

### D4. 测试调整
- `tests/test_account_lifecycle.py`：将「建号未传密码被拒」「建号弱口令被拒」改为「未传密码 → 用 123456 创建成功」（断言 `user.check_password('123456')`）。
- `tests/test_users.py`：`_user_payload` 的 `password` 可去掉（后端默认 123456）；但保留也无害（create 接受显式密码）。
- 保留「update 注入哈希无法接管」「停用失效 token」用例（D3 未回退）。

## Risks / Trade-offs

- **[弱口令 123456]** → 接受（产品决策）。任何知道手机号的人可用 123456 登录。缓解：管理员告知员工尽快改密；后续提案引入随机密码 + 强制首登改密彻底消除。
- **[无强制首登改密]** → 接受。员工可长期不改。后续提案解决。
- **[与 audit-findings account-lifecycle-security R3 冲突]** → 该 spec 未归档（在 `changes/audit-findings/`），两 active change 共存；归档时协调（本提案回退 R3，或合并统一策略）。

## Migration Plan

1. 后端 `apps/users/serializers.py`：`create` 恢复默认 `'123456'`，移除必填报错与 `validate_password`。
2. 前端 `views/Organization.vue`：移除建号密码输入框 + 必填校验。
3. 测试：调整 `test_account_lifecycle.py`（接受 123456）。
4. `pytest` + `npm run build` 验证。
5. 部署：**后端有改动**，需跑 `deploy.sh`（不是仅前端构建）。
- **回滚**：`git revert` 即可。

## Open Questions

1. **登录后是否提示「建议修改初始密码」**？—— *倾向：本提案不做，留待后续「首登强制改密」提案一并处理。*
2. **存量用户（audit-findings 后建的、已有强密码的）是否重置为 123456**？—— *倾向：不重置，本提案只影响新建账号。*
