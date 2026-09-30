## Why

安全审计：建号时 password 可缺省回退硬编码 `123456`，且**显式传入**的密码不经过任何强度校验——建号者可给账号设任意弱口令。同时仓库存在三份互相矛盾的规范（`initial-password-policy` 要求默认 123456 且「接受弱口令」；`password-security` 与 `account-lifecycle-security` 均要求「禁止默认密码 + 必须强度校验」）。用户已拍板产品策略（2026-09-30）：**保留 123456 兜底（分公司行政建号流程不动），显式传入的密码必须过强度校验**——本变更同时落实现与修宪，终结规范冲突。

## What Changes

- `UserSerializer.create`：显式提供 password 时调用 `validate_password(value, 瞬时User(phone,name))`，不通过返回 400（错误挂在 `password` 字段）；缺省回退 `123456` 的行为不变（兜底路径不校验，产品定调）
- 扩展 `AUTH_PASSWORD_VALIDATORS`：在现有最小长度（8）之上新增「纯数字拒绝」与「与用户属性（手机号/姓名）相似拒绝」两个校验器（中文消息，跟随现有自定义模式）——对建号与改密两条路径同时生效
- 修宪三份规范为一致的并存口径：**默认口令策略归 `initial-password-policy`（当前 123456 兜底）；显式密码一律必须通过 `AUTH_PASSWORD_VALIDATORS`**
- update 路径不变（password 本就是 create-only，改密走 `/api/auth/password/`，该接口已有校验并将获得新校验器加持）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `initial-password-policy`: 「建号接受弱口令」场景改为「显式弱口令被拒」；保留「未传回退 123456」；冲突注记更新为已裁决
- `password-security`: 「禁止默认弱口令」条款改为「默认口令策略由 initial-password-policy 规定，本规范约束显式密码强度」
- `account-lifecycle-security`: 「新建用户不得使用默认弱口令」条款同口径对齐

## Impact

- `backend/apps/users/serializers.py`：create() 接入 validate_password
- `backend/apps/authentication/validators.py`：新增两个中文消息校验器
- `backend/rock_slab/settings/base.py`：AUTH_PASSWORD_VALIDATORS 扩两项
- `backend/tests/test_users.py` / `test_auth.py`：新增弱口令拒绝用例与回归
- API 行为变化：显式提交 <8 位、纯数字、与手机号/姓名相似的密码建号从 201 变 400（前端建号表单本就不传密码，无适配需要）；改密接口对纯数字新密码开始拒绝
- 手册无需改（123456 口径保留）；无迁移
