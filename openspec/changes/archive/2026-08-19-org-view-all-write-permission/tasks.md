## 1. 标签可见性（查看全开）

- [x] 1.1 `Organization.vue` 4 个管理标签（区域/分公司/行政组/人员）去掉 `v-if="canManageOrg"`
- [x] 1.2 移除把非管理员切回 `orgchart` 的 `watch(canManageOrg)`；4 个内容容器 `v-else-if` 去掉 `canManageOrg`

## 2. 修改按钮按操作授权

- [x] 2.1 `Organization.vue` 引入 `canManageOrganizations`/`canManageUsers`（替换原 `canManageOrg`）
- [x] 2.2 区域/分公司/行政组的「新增」按钮改 `v-if="canManageOrganizations && activeTab==='X'"`
- [x] 2.3 人员的「新增」按钮改 `v-if="canManageUsers && activeTab==='personnel'"`
- [x] 2.4 子组件编辑/删除按操作授权：`OrganizationRegion`/`OrganizationBranch`/`TeamManager` 用 `canManageOrganizations` gate；`PersonnelManager` 用 `canManageUsers` gate（移除各组件 `canManageOrg` prop，改用本地 `usePermission`）
- [x] 2.5 移除不再使用的 `canManageOrg`（含 `hasMinRole` 解构）

## 3. 验证

- [x] 3.1 前端 `vue-tsc --noEmit` 通过（exit 0）
- [x] 3.2 前端 `vitest` 15 passed（无回归）
- [ ] 3.3 本地手动验证：普通员工能看到 4 个管理标签与数据、看不到修改按钮；持授权者可见可改
