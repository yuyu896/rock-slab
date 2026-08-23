## 1. 后端：模板与任命即授权

- [x] 1.1 `apps/permissions/positions.py`：岗位模板注册表（admin/director/manager/leader/staff，含预填操作码与节点类型提示）；操作码目录 +4（manage_dictionary/manage_instances/adjust_ledger/dispose_assets）
- [x] 1.2 `scope.py`：resolve_user_scope 并入树负责人任命（region manager / team leader / branch manager），Scope 增 appointed_* 集合；任命沿树展开与授权并集
- [x] 1.3 `users/models.py` ROLE_CHOICES 与 `users/views.py` MANAGEABLE_ROLES 去 supervisor；写接口拒绝新 supervisor
- [x] 1.4 删除 `core/permissions.py` 死代码 IsRoleMin / CanApprove
- [x] 1.5 通知路由去角色化：`notifications/signals.py` 审批人=持 approve_transfer（或 admin）且范围内；抄送=持 view_all_notifications 的非 admin 且范围内

## 2. 后端：API 与迁移工具

- [x] 2.1 `GET /api/permissions/position-templates`（岗位模板目录）；`/api/permissions/me` 扩展任命节点 + 生效范围摘要
- [x] 2.2 `GET /api/permissions/effective`（admin，全员生效权限总览，实时派生）
- [x] 2.3 管理命令 `migrate_positions`：默认 dry-run 逐人清单（岗位映射/补授/任命/范围）；--apply 换岗（supervisor→manager）+ 补授模板操作码，不删既有

## 3. 前端

- [x] 3.1 `constants/index.ts` 岗位标签（admin 系统管理员/director 大区负责人/manager 分公司负责人/leader 行政组长/staff 分公司行政；保留 supervisor 兼容展示）；MainLayout/mobile 岗位文案同步
- [x] 3.2 `api/permissions.ts`：position-templates / effective / me 扩展接口与类型
- [x] 3.3 `PermissionAssign.vue` 重构三步（选人→岗位模板→任命节点）+ 实时权限预览 + 特例调整区（沿用既有 ManagementScope/OperationGrant 手工增删）
- [x] 3.4 新增 `PermissionMatrix.vue`（岗位×操作码矩阵 + 用户生效权限卡，Excel 式）+ 路由 `/admin/permission-matrix` + 侧边栏 admin 菜单
- [x] 3.5 移动端 `ApprovalList/ApprovalDetail` canApprove 改 `can('approve_transfer')`；组织页/用户表单岗位下拉去 supervisor

## 4. 测试与验收

- [x] 4.1 后端新增：任命即授权（三种负责人/并集/卸任回收）、岗位模板接口、effective 接口（含 403）、migrate_positions（dry-run/apply 只补不删/supervisor 映射）、通知按操作授权路由
- [x] 4.2 更新受影响测试（test_users 岗位分配线、test_rbac_matrix、test_notifications）；pytest 全绿
- [x] 4.3 前端 vitest / build 通过
- [x] 4.4 浏览器实测：三步分配（任命后范围即时生效）、矩阵页渲染、移动端审批按钮按授权、migrate_positions dry-run 清单
