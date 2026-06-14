## Context

项目全面检查发现 6 个代码质量问题，分散在 3 个前端文件和 3 个后端文件中。这些问题不涉及功能变更或 API 接口调整，均为内部代码质量修复。当前所有问题均在本地未提交的修改分支上，需要在不影响其他正常工作的模块的前提下逐一修复。

**当前状态：**
- `MobileAssign.vue`：form ref 中已移除 `所属部门` 字段，但模板第 146 行仍通过 `v-model="form.所属部门"` 引用
- `MobileAssign.vue`：分支选择器第 128 行使用 `:value="branch.name"`，而 `MobileTransfer.vue` 使用 `:value="branch.id"`
- `types/index.ts`：`Transfer` 接口只有 `from_branch`/`to_branch`（snake_case），前端表单统一使用 `fromBranch`/`toBranch`（camelCase），导致多处 `as any` 转型
- `audit/views.py`：`.extra({'date': "date(created_at)"})` 自 Django 2.x 起弃用
- `reports/views.py`：import 了 `ROLE_LEVELS` 和 `F` 但未使用
- `assets/views.py`：import 了 `IsAdmin` 但未使用

## Goals / Non-Goals

**Goals：**
- 修复 MobileAssign.vue 的运行时警告和数据绑定问题
- 统一移动端视图的分支选择器行为
- 消除 TypeScript 类型不匹配导致的 `as any` 转型
- 清理后端弃用 API 和无用 import
- 保持修改范围最小化，不触碰其他正常工作的模块

**Non-Goals：**
- 不重构 MobileAssign.vue 的整体结构
- 不修改其他视图（MobileTransfer、AssignList 等）的已正常工作的代码
- 不调整 API 接口或序列化器
- 不处理 camelCase/snake_case 全局转换机制
- 不增加新测试用例

## Decisions

### 1. MobileAssign.vue 死引用修复 — 移除而非替换

**决定**：直接移除模板中 `form.所属部门` 的表单组和对应的 v-model 绑定。

**理由**：`所属部门` 字段已从 form ref 中移除是有意的 — 领用操作的 backend serializer 没有对应字段。保留该表单组会提交无用数据。移除模板中的表单组即可消除运行时警告。

### 2. MobileAssign.vue 分支选择器 — 统一使用 branch.id

**决定**：将 `:value="branch.name"` 改为 `:value="branch.id"`。

**理由**：所有其他视图（MobileTransfer、AssignList、TransferList、PurchaseList）均已统一使用 `branch.id` 作为 select 的 value。form 字段 `fromBranch` 的语义也表明它应该是 ID 而非名称。使用 ID 可与 backend 的 `PrimaryKeyRelatedField` 正确匹配。

**同时需要调整**：`currentBranch` 计算属性返回 `userStore.profile?.branch`，这可能是 branch 对象或 ID。需要确保 `fetchOptions` 中对 `form.value.fromBranch` 的赋值使用的是 branch ID。

### 3. Transfer 类型接口 — 添加 camelCase 别名字段

**决定**：在 `Transfer` 接口中添加 `fromBranch?: string` 和 `toBranch?: string` 字段（与已有的 `from_branch`/`to_branch` 并存）。

**理由**：
- 前端表单发送 camelCase（`fromBranch`/`toBranch`），由 `djangorestframework-camel-case` 的 parser 自动转为 `from_branch`/`to_branch`
- 后端序列化器使用 `CamelCaseJSONParser`，所以 `fromBranch` 在服务端会自动映射为 `from_branch`
- 保留 snake_case 字段名是为了兼容 API 响应数据（serializer 的 `CamelCaseJSONRenderer` 会将 `from_branch` 渲染为 `fromBranch`）
- 添加后可消除 `MobileAssign.vue`、`Purchase.vue`、`TransferList.vue` 等文件中的 `as any` 转型

**替代方案（否决）**：将前端所有 camelCase 改为 snake_case — 这违反 JavaScript 命名规范，且与 camelCase parser/render 的设计意图冲突。

### 4. 后端 audit/views.py — 使用 TruncDate 替换 .extra()

**决定**：将 `AuditLog.objects.filter(...).extra({'date': "date(created_at)"}).values('date')` 替换为 `AuditLog.objects.filter(...).annotate(date=TruncDate('created_at')).values('date')`。

**理由**：`.extra()` 自 Django 2.x 起弃用，推荐使用 `TruncDate` 函数。功能完全等价，输出相同的 `date` 字段。

### 5. 后端 import 清理 — 直接删除

**决定**：删除 `reports/views.py` 中未使用的 `ROLE_LEVELS` 和 `F`，删除 `assets/views.py` 中未使用的 `IsAdmin`。

**理由**：这些 import 确实未在代码中使用，删除不会影响任何功能。

## Risks / Trade-offs

- **[低风险] MobileAssign.vue 移除所属部门表单**：用户界面上少了一个输入框，但该字段在 backend 不存在，之前提交也会被忽略。→ 无需迁移。
- **[低风险] branch.id 替换 branch.name**：如果 `currentBranch` computed 返回的是 branch name 而非 ID，表单初始化时分支选择器可能无法匹配。→ 需要检查 `userStore.profile?.branch` 的实际值类型。
- **[极低风险] TruncDate 替换 .extra()**：功能完全等价。→ 不同数据库引擎的 `TruncDate` 实现均为 Django 内置支持。
