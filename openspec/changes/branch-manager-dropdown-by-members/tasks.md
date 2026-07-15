## 1. 前端分公司负责人下拉

- [x] 1.1 `Organization.vue` 分公司表单「负责人」options 由 `users.filter(角色 in leader+)` 改为 `users.filter(u => u.branch === editingItem.id)`（去角色限制、按分公司归属）
- [x] 1.2 「负责人」改可选：去 `<span class="required">*</span>`（提交逻辑本就 `manager: item.manager || null`，无需改校验）

## 2. 验证

- [x] 2.1 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 2.2 本地手动验证：编辑既有分公司 → 负责人下拉=该分公司成员(含 staff)、不含他司；新分公司可留空负责人
