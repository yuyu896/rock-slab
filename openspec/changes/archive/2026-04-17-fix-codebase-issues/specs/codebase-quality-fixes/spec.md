## ADDED Requirements

### Requirement: MobileAssign 模板不引用已删除的表单字段
`MobileAssign.vue` 的模板中 SHALL NOT 包含对 form ref 中不存在的字段的 v-model 绑定。具体地，`所属部门` 字段已从 form ref 中移除，模板中 SHALL NOT 存在 `v-model="form.所属部门"` 或任何引用该字段的表单组。

#### Scenario: 模板无死引用
- **WHEN** MobileAssign.vue 组件渲染
- **THEN** 不产生 Vue 运行时警告，所有 v-model 绑定的字段均存在于 form ref 定义中

### Requirement: MobileAssign 分支选择器使用 branch.id
`MobileAssign.vue` 的分支选择器 SHALL 使用 `branch.id` 作为 option 的 value，与 `MobileTransfer.vue` 等其他移动端视图保持一致。

#### Scenario: 分支选择器提交 ID
- **WHEN** 用户在 MobileAssign 页面选择一个分公司
- **THEN** 表单中的 `fromBranch` 字段值 SHALL 为该分公司的 UUID，而非分公司名称

#### Scenario: 分支选择器与其他视图一致
- **WHEN** 比较 MobileAssign.vue 和 MobileTransfer.vue 的分支选择器
- **THEN** 两者的 `:value` 绑定 SHALL 使用相同的属性（`branch.id`）

### Requirement: Transfer 类型接口包含 camelCase 分支字段
`types/index.ts` 中的 `Transfer` 接口 SHALL 同时包含 `fromBranch?: string` 和 `toBranch?: string` 字段，与已有的 `from_branch`/`to_branch` 字段并存。前端代码中创建流转记录时的 payload 类型 SHALL NOT 需要 `as any` 强制转型。

#### Scenario: 表单提交无类型错误
- **WHEN** 前端表单构造包含 `fromBranch` 或 `toBranch` 的 payload 并调用 API 函数
- **THEN** TypeScript 编译 SHALL 通过，无需 `as any` 转型

### Requirement: 审计日志统计使用 TruncDate 替代 extra
`audit/views.py` 的 `statistics` action SHALL 使用 `django.db.models.functions.TruncDate` 实现 `created_at` 的日期提取，SHALL NOT 使用已弃用的 `.extra()` 方法。

#### Scenario: 日期分组统计功能不变
- **WHEN** 调用 `/api/audit/statistics` 接口
- **THEN** 返回的每日统计数据格式和内容 SHALL 与使用 `.extra()` 时完全一致

### Requirement: 后端无未使用的 import
`reports/views.py` SHALL NOT import `ROLE_LEVELS`（来自 `core.permissions`）或 `F`（来自 `django.db.models`）。`assets/views.py` SHALL NOT import `IsAdmin`（来自 `core.permissions`）。

#### Scenario: 代码库无 lint 警告
- **WHEN** 对后端 Python 文件执行静态分析
- **THEN** `reports/views.py` 和 `assets/views.py` SHALL 无 "unused import" 警告
