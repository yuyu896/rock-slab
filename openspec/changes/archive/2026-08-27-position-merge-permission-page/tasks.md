## 1. 后端：岗位模板与角色模型

- [x] 1.1 `apps/permissions/positions.py`：manager 模板改「分公司行政」（scope_type=branch，8 操作码：manage_users/manage_dictionary/manage_assets/approve_transfer/approve_inventory/adjust_ledger/manage_instances/view_reports）；删除 staff 模板；`LEGACY_POSITION_MAP` 增 `'staff': 'manager'`
- [x] 1.2 `apps/users/models.py`：ROLE_CHOICES 去 staff，默认 role 改 `manager`；生成配套 migration（纯 DDL AlterField，不掺 DML）
- [x] 1.3 `apps/users/views.py`：`MANAGEABLE_ROLES` 收敛四岗（leader→[]）；perform_create 默认 target_role 改 `manager`；删除"leader 只能建 staff"死代码块
- [x] 1.4 `core/management/commands/seed_data.py`：种子用户 role staff→manager
- [x] 1.5 `apps/permissions/management/commands/check_seed_grants.py`：leader/staff 授权校验循环改仅 leader；新增存量 supervisor/staff 活跃用户 WARN（提示运行 migrate_positions --apply）

## 2. 前端：角色常量与页面同步

- [x] 2.1 `constants/index.ts`：ROLE_LABELS 四岗化（manager→分公司行政、staff→分公司行政（已退役））；ROLE_LEVELS 收敛 admin1/director2/manager3/leader4，supervisor5/staff6 仅存量展示
- [x] 2.2 `MainLayout.vue`、`mobile/Home.vue`、`mobile/Profile.vue`：本地 roleLabels 映射删除，统一引用 `ROLE_LABELS`
- [x] 2.3 `Organization.vue`：员工表单岗位选项四岗化（存量 staff/supervisor 动态追加"已退役"禁用选项）；新员工默认 role 改 `manager`；删除弹窗内不可达的 user 字段死代码块
- [x] 2.4 `PermissionAssign.vue`：默认岗位 fallback 改 `manager`

## 3. 前端：权限分配页脏检查与只补不删

- [x] 3.1 `onPickRole` 改并集预填：`draftOps = 模板操作码 ∪ 既有授权码集`（admin 用户维持禁用现状）
- [x] 3.2 保存可用条件改 `岗位变化 || draftOps 与既有授权码集存在差集`
- [x] 3.3 操作码区下方增保留提示："将保留岗位外的既有授权 N 项（显式取消勾选才删除）"，N 随勾选实时计算，N=0 不显示
- [x] 3.4 保存逻辑核对：维持差量对齐（增缺删多），确认与并集预填组合后默认保存只增不删

## 4. 测试与验证

- [x] 4.1 后端 pytest：更新 `test_position_permissions.py`（四岗目录、manager 模板 8 操作码、staff 创建 400、存量 staff 不炸、migrate_positions staff→manager 只补不删）；修复其余受影响测试（choices/目录断言）
- [x] 4.2 前端 `npm run build`（类型门禁）+ `npm run test`（vitest）
- [x] 4.3 手动核对：权限分配页换岗场景（含模板外授权的用户）不丢权限；仅勾选操作码时保存按钮可用（浏览器实测：M3 staff→分公司行政，8 模板 ∪ dispose_assets 并集预填、保留提示 N=1、保存落库 dispose_assets 保留、仅勾操作码双向切换保存按钮启用/禁用）

## 5. 收尾

- [x] 5.1 CLAUDE.md 权限系统行同步四岗口径；v2-revision-draft.md §八 第 5 案状态改 ✅
- [ ] 5.2 feat + openspec 两 commit → push → 归档；部署后服务器跑 `migrate_positions`（dry-run 核对 → --apply）
