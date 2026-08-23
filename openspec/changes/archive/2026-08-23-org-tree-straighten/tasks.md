## 1. 后端模型与迁移

- [x] 1.1 `organizations/models.py`：`Branch.team` 改必填 + `on_delete=PROTECT`，删 `Branch.region`
- [x] 1.2 `users/models.py`：删 `User.region` / `User.team` / `User.leader`
- [x] 1.3 `organizations` 新迁移：纯 Python 回填（员工众数 → 「{区域名}未分组」兜底组，输出清单日志）→ AlterField(team 非空 PROTECT) → RemoveField(region)；`users` 新迁移删三列并依赖 organizations 迁移顺序
- [x] 1.4 删除 `assign_branch_team_from_employees` 管理命令；`makemigrations --check` 无漂移

## 2. 后端接口与范围

- [x] 2.1 `organizations/serializers.py`：BranchSerializer 删可写 region、加只读派生 `region`（= team.region）、team 必填、删一致性校验；TeamSerializer `member_count` 改组内分公司员工数
- [x] 2.2 `organizations/views.py`：BranchViewSet select_related 改 team 链路；TeamViewSet 删组长回写、perform_destroy 捕获 ProtectedError 返回 400
- [x] 2.3 `organizations/filters.py`：`?region=` 改过滤 `team__region_id`
- [x] 2.4 `permissions/scope.py` + `core/permissions.py`：树遍历展开（region→team→branch、team→branch 全并入 branches），删 DataScopeMixin 死代码 `scope_team_field`
- [x] 2.5 `users/{serializers,views}.py`：UserSerializer 删 region/leader/team 字段、region_name 由 branch.team.region 派生；视图删 `Q(region__in)`、`_validate_in_scope` 只查 branch、删 supervisor 自动填 region、select_related 更新

## 3. 前端组织页

- [x] 3.1 `types/index.ts`：User 删 region/leader/team；Branch.region 标注为派生只读
- [x] 3.2 `utils/orgTree.ts`：`filterEmployeesByNode` 改沿树派生 + 负责人并入（branch.manager / team.leader / region.manager），删未分组分支
- [x] 3.3 `Organization.vue`：树删未分组节点；分公司表单改选行政组（派生区域显示）；员工表单删区域/行政组下拉；移动弹窗删未分组、提交只带 branch；员工表「所属组织」由 branch 派生
- [x] 3.4 删除死代码子页 `views/organization/{PersonnelManager,TeamManager,OrganizationBranch,OrganizationRegion}.vue`

## 4. 测试

- [x] 4.1 后端：更新 test_organizations / test_users / test_user_profile_branch / test_data_scoping / test_management_permissions / test_asset_crud / test_transfers / test_import_export 等中 region/team/leader 构造与断言（分公司建行改传 team）
- [x] 4.2 后端新增：回填迁移测试（众数/兜底组/约束生效）、树遍历范围测试（region 授权穿透行政组）、行政组删除保护测试、组长不回写测试
- [x] 4.3 前端：orgTree 派生规则测试更新/新增；`npm run test`、`npm run build` 通过
- [x] 4.4 `pytest` 全绿

## 5. 验收

- [x] 5.1 本地拉起实测：组织树层级 集团→区域→行政组→分公司、无未分组节点；创建/移动员工只写分公司；组长/区长在节点可见
- [x] 5.2 迁移在本地 SQLite 全量重放（fresh migrate）无错
