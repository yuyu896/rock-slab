## Why

当前组织架构模块存在两个问题：

**问题 1：低角色用户看不到侧边栏员工**

后端 `UserViewSet` 的 `min_role = 'supervisor'`，导致 leader/staff 调用用户列表 API 时直接返回 403 拒绝。而 `_get_user_queryset` 中 leader 只能看到本分公司的 staff，staff 只能看到自己。前端侧边栏依赖 `fetchUsers()` 获取全部用户来构建组织架构树，API 被拒后侧边栏为空。

业务需求是：所有角色都应能在侧边栏看到集团内全部员工（只读展示），不需要数据隔离。只有 supervisor 及以上才能查看并编辑"区域管理"、"分公司管理"、"行政组"、"人员管理"标签页。

**问题 2：无权限操作时弹出错误提示**

当 leader/staff 用户在组织架构标签页中点击编辑（如保存用户信息）时，后端返回 403 错误，前端通过 `handleApiError` 弹出 `ElMessage.error` 显示"您没有执行该操作的权限"。但既然已经通过标签页可见性做了权限隔离（supervisor 以下不显示管理标签页），不应再出现权限报错弹窗。

## What Changes

- 后端用户列表接口降低访问门槛：`list` 和 `retrieve` action 的 `min_role` 从 `supervisor` 降为 `staff`，所有已认证用户均可查看全部用户列表（返回完整数据集，不做数据隔离过滤）
- 后端写入操作权限不变：`create`、`update`、`destroy` 仍要求 `supervisor` 及以上
- 前端标签页可见性调整：`canManageOrg` 的判断从 `hasMinRole('manager')` 改为 `hasMinRole('supervisor')`，supervisor 及以上可见全部标签页，leader/staff 仅可见"组织架构"和"人员管理"（只读）
- 前端隐藏无权限的编辑操作：leader/staff 在"人员管理"标签页中不显示新增/编辑/删除按钮，从根源避免权限报错弹窗

## Capabilities

### Modified Capabilities

- `user-list-api`: 用户列表接口对所有已认证角色开放只读访问
- `org-role-visibility`: 标签页可见性阈值从 manager 调整为 supervisor
- `org-personnel-readonly`: leader/staff 的人员管理标签页为纯只读

## Impact

- **后端视图**: `apps/users/views.py` 的 `UserViewSet` 需调整 `list`/`retrieve` 的 `min_role` 和 `get_queryset`
- **前端视图**: `Organization.vue` 的 `canManageOrg` 阈值改为 supervisor；人员管理标签页的增删改按钮加权限守卫
- **API 兼容性**: 用户列表接口对 leader/staff 不再返回 403，改为返回全量用户数据
