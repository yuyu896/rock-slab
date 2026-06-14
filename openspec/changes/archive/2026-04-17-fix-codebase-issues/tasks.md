## 1. 后端代码清理

- [x] 1.1 清理 `assets/views.py`：移除未使用的 `IsAdmin` import
- [x] 1.2 清理 `reports/views.py`：移除未使用的 `ROLE_LEVELS` 和 `F` import
- [x] 1.3 修复 `audit/views.py`：将 `.extra({'date': "date(created_at)"})` 替换为 `TruncDate('created_at')`，添加对应的 import

## 2. 前端类型定义修复

- [x] 2.1 在 `types/index.ts` 的 `Transfer` 接口中添加 `fromBranch?: string` 和 `toBranch?: string` 字段

## 3. MobileAssign.vue 修复

- [x] 3.1 移除模板中引用 `form.所属部门` 的"使用部门"表单组（第 143-151 行）
- [x] 3.2 将分支选择器的 `:value="branch.name"` 改为 `:value="branch.id"`（第 128 行）
- [x] 3.3 检查 `currentBranch` 计算属性赋值逻辑，确保 `form.value.fromBranch` 接收的是 branch ID
- [x] 3.4 移除 `handleSubmit` 中 `assignAsset` 调用的 `as any` 类型断言
