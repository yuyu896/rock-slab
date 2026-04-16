## 组织架构全员可见 + 权限弹窗消除 — 技术设计

### 1. 后端：用户列表接口降门槛

文件：`apps/users/views.py`

#### 1.1 调整 min_role

当前 `UserViewSet.get_permissions()` 中 `list`/`retrieve` 的 `min_role = 'supervisor'`，改为 `'staff'`：

```python
if self.action == 'list' or self.action == 'retrieve':
    self.min_role = 'staff'  # 所有角色可查看用户列表
```

#### 1.2 list action 返回全量数据

当前 `get_queryset()` 调用 `_get_user_queryset()`，对 leader 只返回本分公司 staff，对 staff 只返回自己。需要区分只读和写入场景：

方案：在 `get_queryset` 中判断 action，`list`/`retrieve` 时返回全量，其他 action 保持原有过滤。

```python
def get_queryset(self):
    if self.action in ('list', 'retrieve'):
        return User.objects.select_related('branch', 'region', 'leader', 'created_by').all()
    return _get_user_queryset(self.request.user)
```

这样写入操作（create/update/destroy）仍使用 `_get_user_queryset` 做权限校验。

### 2. 前端：标签页可见性调整为 supervisor

文件：`frontend/src/views/Organization.vue`

当前 `canManageOrg` 定义为：

```typescript
const canManageOrg = computed(() => hasMinRole('manager'))
```

改为：

```typescript
const canManageOrg = computed(() => hasMinRole('supervisor'))
```

这样 supervisor 可以看到区域管理、分公司管理、行政组、人员管理（含编辑），leader/staff 只看到组织架构和人员管理（只读）。

### 3. 前端：人员管理标签页只读控制

文件：`frontend/src/views/Organization.vue`

在人员管理标签页中，"新增人员"按钮和每行的"编辑"/"删除"操作按钮需加 `v-if="canManageOrg"` 条件：

- 标签页工具栏的"新增人员"按钮加 `v-if="canManageOrg"`
- 人员列表每行的编辑/删除按钮加 `v-if="canManageOrg"`
- 这样 leader/staff 看到的是纯只读的人员列表，不会触发任何写入操作，从根源避免权限报错弹窗

### 4. 不做的事

- **不修改 `_get_user_queryset` 本身**：写入操作的权限校验逻辑保持不变
- **不修改前端 handleApiError**：权限弹窗的根因是不该出现写入操作入口，而非错误提示本身有问题
- **不修改侧边栏逻辑**：`fetchUsers()` 已能获取全量数据（修复后端后自动生效），侧边栏 `buildOrgTree` 无需改动
