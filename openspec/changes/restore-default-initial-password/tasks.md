## 1. 后端：恢复默认初始密码

- [x] 1.1 `apps/users/serializers.py` 的 `UserSerializer.create`：`password = validated_data.pop('password', '123456')`（恢复默认）；移除「未传 password 报 400」与 `password_validation.validate_password` 调用；清理不再使用的 import（`password_validation` / `DjangoValidationError`，若他处不用）。
- [x] 1.2 确认 `update` 方法的 password create-only（防账号接管）**保留不动**（D3）。
- [x] 1.3 调整测试 `tests/test_account_lifecycle.py`：「建号未传密码被拒」「建号弱口令被拒」改为「未传密码 → 201 且 `check_password('123456')` 为真」；保留「update 注入哈希无法接管」「停用失效 token」用例。
- [x] 1.4 `tests/test_users.py` 的 `_user_payload` 可去掉 `password`（后端默认 123456）；确认 TestUserCRUD/TestRoleAssignment/TestAutoAssignment 通过。

## 2. 前端：去掉建号密码输入框

- [x] 2.1 `views/Organization.vue`：移除建号表单的「初始密码」`<input>`（`v-if="editingItem.isNew"` 那块）。
- [x] 2.2 `addItem('users')`：恢复不预填 password（去掉 `password: ''` 或保留无妨，因不传后端用默认）。
- [x] 2.3 `createUser` 分支：不再传 `payload.password`、不再做 ≥8 位必填校验（移除那段 `if (!item.password || ...)` 校验）。
- [x] 2.4 编辑用户分支保持不提交 password（现状，配合 create-only）。

## 3. 验证

- [x] 3.1 `pytest --tb=short -q` 全绿（含调整后的 account-lifecycle 用例）。
- [x] 3.2 `npm run build` 通过。
- [x] 3.3 手动验证：建号不填密码 → 成功 → 用 123456 登录成功 → 改密后用新密码登录。
- [x] 3.4 `openspec validate restore-default-initial-password` 通过。

## 4. 提交与部署

- [x] 4.1 拆两个 commit：`feat: 建号恢复默认初始密码 123456`（后端 + 前端 + 测试）+ `chore(openspec): restore-default-initial-password 提案`。
- [x] 4.2 部署：**后端有改动**，跑 `deploy.sh`（git pull → build backend → migrate → 前端 build → nginx reload）；无新迁移，migrate 为 no-op。
- [x] 4.3 部署后验证线上建号流程（建号 → 123456 登录 → 改密）。
