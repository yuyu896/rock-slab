## 组织架构全员可见 + 权限弹窗消除 — 任务清单

### 后端

- [ ] T1: `apps/users/views.py` — `UserViewSet.get_permissions()` 中 `list`/`retrieve` 的 `min_role` 从 `'supervisor'` 改为 `'staff'`
- [ ] T2: `apps/users/views.py` — `UserViewSet.get_queryset()` 中 `list`/`retrieve` action 返回全量用户数据，其他 action 保持 `_get_user_queryset` 过滤

### 前端

- [ ] T3: `Organization.vue` — `canManageOrg` 阈值从 `hasMinRole('manager')` 改为 `hasMinRole('supervisor')`
- [ ] T4: `Organization.vue` — 人员管理标签页的"新增人员"按钮加 `v-if="canManageOrg"` 条件
- [ ] T5: `Organization.vue` — 人员列表中每行的"编辑"/"删除"操作按钮加 `v-if="canManageOrg"` 条件

### 验证

- [ ] T6: 以 staff 角色登录，确认侧边栏能看到全部员工
- [ ] T7: 以 staff 角色登录，确认只看到"组织架构"和"人员管理"标签页，人员管理中无编辑按钮
- [ ] T8: 以 supervisor 角色登录，确认能看到全部标签页并可编辑
