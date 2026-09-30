## 1. 实现

- [x] 1.1 `backend/apps/authentication/validators.py` 新增两个中文消息校验器：`NumericPasswordValidator`（纯数字拒绝）、`UserAttributeSimilarityValidator`（与手机号/姓名相似拒绝；内置消息为内联英文，故以 try/super 覆写转换）
- [x] 1.2 `backend/rock_slab/settings/base.py` 的 `AUTH_PASSWORD_VALIDATORS` 追加上述两项（相似性校验显式配置 `user_attributes=['phone','name']`——默认属性表在本项目自定义 User 上不存在，不配则形同虚设）
- [x] 1.3 `backend/apps/users/serializers.py` 的 `create()`：显式提供 password 时 `validate_password(value, User(phone=…, name=…))`，Django ValidationError 转 `serializers.ValidationError({'password': messages})`；兜底路径不变

## 2. 测试

- [x] 2.1 新增用例：显式弱口令（<8 位 / 纯数字 / 与手机号相似）建号 → 400 且不落库；显式强口令 → 201；未传密码 → 201 且 check_password('123456')（兜底回归）；反转旧「接受弱口令」用例（test_account_lifecycle）
- [x] 2.2 改密接口回归（新校验器生效路径）+ 全量 `pytest` 通过（875 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（建号弹窗经 API 显式传弱口令应 400；正常建号流程不受影响）

> 手验要点：本地或部署后，用 curl/前端接口工具以管理员建号分别传 `password: 12345678`（应 400 提示纯数字）与不传 password（应 201 正常建号，初始密码 123456）；人员管理页正常建号流程应无感知变化。
