## Why

`audit-findings-remediation`（task 3.2 / 3.3，已上线）移除了建号默认密码 `123456`，改为建号必填密码 + 强度校验。但实际使用中，管理员为每个新员工单独设密码较繁琐，且现场分发初始密码不便。**产品决策：临时恢复**「建号默认初始密码 123456 + 员工登录后自行修改」的简化流程，降低管理员负担。

**这是有意识的权衡量决策**：以弱口令风险换取建号便捷。后续待系统其他功能完善后，将重新设计安全的初始密码方案（随机密码 + 首登强制改密），届时再消除弱口令。

## What Changes

- **回退 audit-findings task 3.2**：`UserSerializer.create` 恢复默认密码 `'123456'`（未传 password 时回退 123456）；不再强制 password 必填、不再走 `password_validation`（接受 `123456` 作为初始密码）。
- **回退 audit-findings task 3.3**：前端 `views/Organization.vue` 建号表单移除「初始密码」输入框，恢复到「建号无需填密码」状态。
- 员工用 `123456` 首次登录后，可通过 `/api/auth/password/`（已有）自行修改密码。
- **保留** audit-findings 的其他安全改动（密码 update 防接管、停用失效 token、写越权防护、盘点并发等均不受影响）。

## ⚠️ 已知风险（接受，后续消除）

- **弱口令**：所有新建账号初始密码为 `123456`。任何知道员工手机号的人都可用 `123456` 登录，存在账号接管风险。
- **无强制首登改密**：员工可长期不改密码，弱口令持续有效。
- **缓解**：管理员建号后通过渠道告知员工尽快改密；后续重新设计时引入强制首登改密。

## 后续计划（待系统功能完善后）

重新设计安全的初始密码方案，消除上述风险：
- 建号生成**随机初始密码**（非固定值）；
- 员工**首次登录强制改密**（初始密码只用一次）；
- 届时以新提案替换本策略。

## Capabilities

### New Capabilities

- `initial-password-policy`: 建号默认初始密码 123456，员工登录后自行修改；接受弱口令作为初始值（临时策略，已知风险，后续消除）。

### Modified Capabilities

（无。本提案与 `audit-findings-remediation` 的 `account-lifecycle-security` R3「新建用户不得使用默认弱口令」**直接冲突**——该 requirement 尚未归档进 `openspec/specs/`，待两提案一并归档时协调：本提案回退该项，或合并为统一密码策略。）

## Impact

- **后端**：`apps/users/serializers.py`（`UserSerializer.create` 恢复默认 `'123456'`，去掉必填 + `validate_password`）。
- **前端**：`views/Organization.vue`（建号表单移除密码输入框 + 必填校验；`addItem` 恢复不预填密码）。
- **测试**：`tests/test_account_lifecycle.py` 的「建号未传密码被拒 / 弱口令被拒」用例需调整为「接受 123456」；`tests/test_users.py` 的 `_user_payload` 可去掉 password。
- **不受影响**：密码 update 防接管、停用失效 token、写越权防护等 audit-findings 其他改动保留。
- **风险**：弱口令（已知，接受，后续消除）。
