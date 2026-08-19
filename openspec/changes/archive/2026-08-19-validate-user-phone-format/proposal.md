## Why

当前创建用户时，手机号字段 `phone`（`CharField(max_length=20)`）没有任何格式校验。前端表单和后端接口均接受任意字符串作为手机号，导致可以创建手机号为空格、字母、少于或多于 11 位数字的无效用户。这些无效用户后续无法通过手机号正常登录，也无法被其他用户识别联系。

需要在前端和后端同时增加校验，确保手机号必须是精确 11 位纯数字。

## What Changes

- 后端模型验证：在 `UserSerializer` 的 `phone` 字段上增加 `RegexValidator`，限定必须为 11 位纯数字，创建和更新时均生效
- 后端登录校验：`PhoneModelBackend` 在认证前先校验手机号格式，格式不匹配时直接返回认证失败而非触发数据库查询
- 前端输入限制：创建/编辑用户表单的手机号 `<input>` 增加 `maxlength="11"` 和 `type="tel"` 属性，并增加前端实时校验提示
- 前端登录表单：登录页手机号输入框同样增加格式校验

## Capabilities

### New Capabilities

- `phone-format-validation`: 手机号 11 位纯数字格式校验，前后端双重验证

### Modified Capabilities

- `user-management`: 用户创建/编辑流程增加手机号格式校验
- `user-login`: 登录流程增加手机号格式前置校验

## Impact

- **后端序列化器**: `apps/users/serializers.py` 的 `UserSerializer` 需增加 `phone` 字段验证规则
- **前端表单**: `Organization.vue` 的用户编辑表单和 `Login.vue` 的登录表单需增加输入限制和校验提示
- **API 兼容性**: 用户创建/更新接口在手机号格式不合规时返回 400 错误，错误信息为 `手机号必须为11位数字`
- **现有数据**: 不影响已有用户数据，仅在创建和更新时校验
