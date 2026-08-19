## 手机号格式校验 — 任务清单

### 后端

- [ ] T1: 在 `apps/users/serializers.py` 的 `phone` 字段增加 `RegexValidator(r'^\d{11}$')`，错误信息为"手机号必须为11位数字"
- [ ] T2: 在 `apps/users/authentication.py` 的 `PhoneModelBackend.authenticate()` 入口增加手机号格式前置校验（非 11 位数字直接返回 None）
- [ ] T3: 验证后端校验生效：创建手机号为 10 位 / 12 位 / 含字母时返回 400 错误

### 前端

- [ ] T4: 在 `Organization.vue` 用户编辑表单的手机号 `<input>` 增加 `maxlength="11"` 和 `type="tel"` 属性
- [ ] T5: 在 `Organization.vue` 用户提交前增加手机号格式校验 `/^\d{11}$/`，不通过时 `ElMessage.warning('手机号必须为11位数字')` 并阻止提交
- [ ] T6: 在 `Login.vue` 登录表单的手机号 `<input>` 增加 `maxlength="11"` 和提交前校验

### 验证

- [ ] T7: 端到端验证：前端输入 10 位手机号时提示错误；后端直接调用 API 传入 12 位数字时返回 400
