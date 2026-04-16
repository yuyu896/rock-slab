## Why

当前组织架构模块的左侧边栏"新增人员"按钮仅通过弹窗表单操作，缺乏对人员的集中管理视图。管理员需要一个专门的"人员管理"标签页，以表格形式浏览、搜索、筛选所有员工账号，并高效完成开通、编辑、启停、删除等账号生命周期管理操作。

## What Changes

- 在组织架构页面新增"人员管理"标签页，与现有"组织架构"、"区域管理"、"分公司管理"并列
- 提供人员列表表格视图，支持按姓名/手机号搜索、按角色/区域/分公司/状态筛选
- 新增人员功能：填写姓名、手机号、角色、所属区域、所属分公司、直属上级，设置初始密码
- 编辑人员功能：修改人员基本信息和账号状态
- 启用/停用账号：切换账号的 active/inactive 状态
- 删除人员：确认后删除账号

## Capabilities

### New Capabilities
- `personnel-management`: 人员管理标签页，包含人员列表（搜索、筛选）、新增人员、编辑人员、启用/停用账号、删除人员的完整 CRUD 功能

### Modified Capabilities

## Impact

- 前端：`Organization.vue` 新增标签页及对应模板、脚本、样式
- 后端：复用现有 `UserViewSet`（`/api/users/`）的 CRUD 接口，无需新增后端 API
- 复用已有 API 模块：`@/api/users`（getUsers, createUser, updateUser, deleteUser）
