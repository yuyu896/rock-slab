## ADDED Requirements

### Requirement: 改密成功后保持登录态
个人中心修改密码成功后，系统 MUST 使用后端返回的新 Token 更新本地凭证（`localStorage('rock_slab_token')` 与 Pinia store），用户 MUST 保持登录、不得被跳转到登录页。

#### Scenario: 修改密码成功且会话保持
- **WHEN** 用户在个人中心输入正确原密码与新密码并提交成功
- **THEN** 本地 Token 被更新为新 Token，用户留在当前界面保持登录，后续请求不返回 401

#### Scenario: 改密后可继续访问受保护接口
- **WHEN** 修改密码成功后用户立即进行任意需认证的操作（如刷新列表）
- **THEN** 请求携带新 Token 并成功返回，不触发登录跳转

### Requirement: 改密失败展示真实原因
修改密码失败时，系统 MUST 向用户展示后端返回的真实原因（如"原密码错误"），不得仅显示通用的"密码修改失败"。

#### Scenario: 原密码错误时显示后端原因
- **WHEN** 用户提交的原密码与账户实际密码不符
- **THEN** 界面展示后端返回的 `detail` 错误信息（如"原密码错误"），而非通用的失败文案
