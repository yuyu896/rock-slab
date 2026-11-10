## 1. 后端模型与迁移

- [x] 1.1 在 `backend/apps/users/models.py` 的 `User` 模型新增 `team` 外键：`team = models.ForeignKey('organizations.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name='所属行政组')`
- [x] 1.2 运行 `python manage.py makemigrations users` 生成迁移文件，确认迁移仅加 nullable 列、无数据回填
- [x] 1.3 本地运行 `python manage.py migrate` 验证迁移成功

## 2. 后端序列化

- [x] 2.1 在 `backend/apps/users/serializers.py` 的 `UserSerializer` 新增只读字段 `team`（uuid）和 `teamName`（`source='team.name'`）；`UserWriteOptionSerializer` / `UserDeleteOptionSerializer` 视需要同步加 `team` 写入字段
- [x] 2.2 在 `UserSerializer.validate()` 中实现 branch/team 互斥：`branch` 非空时将 `team` 置为 None；两者均传入时以 `branch` 为准并清空 `team`
- [x] 2.3 确认 `select_related` 在 `UserViewSet.queryset` 和 `_get_user_queryset` 中加入 `'team'`（含 `'team__region'` 若需回填区域名）

## 3. 后端过滤

- [x] 3.1 在 `backend/apps/users/filters.py` 的 `UserFilterSet` 新增 `team` 过滤字段（`django_filters.UUIDFilter` 或 CharField，按 `team_id` 精确匹配）

## 4. 后端数据范围兜底

- [x] 4.1 在 `backend/apps/permissions/scope.py` 的 `resolve_user_scope` 默认兜底段（无显式 ManagementScope 时）：`branch` 为空且 `team_id` 有值时，查询 `Branch.objects.filter(team_id=team_id)` 的 id 集合加入 `Scope.branches`
- [x] 4.2 确认 `Scope.teams` 字段在默认兜底路径也填入该 team_id（供下游 team 路径判断复用）

## 5. 后端用户视图范围校验

- [x] 5.1 `UserViewSet._get_user_queryset`：除现有 `Q(branch__in=scope.branches)` 外，新增 `Q(team__in=scope.teams)` 分支（team 直属员工可见）
- [x] 5.2 `UserViewSet._validate_in_scope`：第 494 行 `in_branch` 判断后追加 `in_team` 回退——target 的 `team_id` 有值且其对应分公司集合 ⊆ `scope.branches`（或 `scope.all`）则通过
- [x] 5.3 `UserViewSet._validate_delete_scope`：同样追加 team 路径回退判断
- [x] 5.4 `UserViewSet._validate_target_branch_in_scope`：若改为允许 target team，需同步校验 target team 在操作者范围内（若仅校验 branch 则 team 提交无校验，按设计 team 兜底由 scope 处理即可，确认无需额外校验）

## 6. 后端测试

- [x] 6.1 新增测试：创建员工 `branch=null, team=<id>`，断言 `team` 保存、`branch` 为 null
- [x] 6.2 新增测试：创建员工 `branch=<id>, team=<id>`，断言 `team` 被清空为 null、`branch` 保存
- [x] 6.3 新增测试：仅归属行政组员工的 `resolve_user_scope` 默认范围含该 team 下分公司
- [x] 6.4 新增测试：`_validate_in_scope` 对 team 直属员工的通过/拒绝两种情况
- [x] 6.5 运行 `pytest backend/tests/test_permissions.py backend/tests/test_organizations.py` 确认无回归

## 7. 前端类型

- [x] 7.1 在 `frontend/src/types/index.ts` 的 `User` 接口新增 `team?: string | null` 和 `teamName?: string`

## 8. 前端员工过滤函数

- [x] 8.1 在 `frontend/src/utils/orgTree.ts` 的 `filterEmployeesByNode` team 分支追加 `|| (u.team && u.team === node.rawId)`
- [x] 8.2 在 region 分支追加 `|| (u.team && teamIds.has(u.team))`（teamIds 已有，复用）

## 9. 前端员工编辑表单

- [x] 9.1 在 `frontend/src/views/Organization.vue` 的 `editUser()` 初始化对象加入 `team: u.team || ''`
- [x] 9.2 在 `addItem('user')` 初始化对象：当选中 team 节点且无 branch 时预填 `team`；选中 branch 节点时预填 `branch`（已有），team 留空
- [x] 9.3 员工编辑表单新增「所属行政组」字段：`branch` 有值时只读显示派生 `teamName`（从 `branches.find(b=>b.id===branch).teamName` 或 team 列表），`branch` 为空时为可选下拉（列全部行政组，按区域 optgroup 分组）
- [x] 9.4 `saveEmployee()` 提交 payload：`branch: e.branch || null, team: e.branch ? null : (e.team || null)`（互斥由前端保证，后端再兜底）

## 10. 前端移动员工弹窗

- [x] 10.1 改造移动弹窗为三段：区域下拉（可选）→ 行政组下拉（随区域联动，可选）→ 分公司下拉（随行政组联动，可选，列该组下分公司）
- [x] 10.2 `moveState` 结构改为 `{ employee, region, team, branch }`，新增联动 computed：`filteredMoveTeams`（按选 region 过滤）、`filteredMoveBranches`（按选 team 过滤）
- [x] 10.3 保留分公司搜索框（在分公司下拉上方），按分公司名称/编号筛选 `filteredMoveBranches`
- [x] 10.4 `confirmMove()` 提交逻辑：`branch` 有值 → `{branch: id, team: null}`；`branch` 空但 `team` 有值 → `{branch: null, team: id}`；均空 → `{branch: null, team: null}`；成功提示文案随三种情况区分
- [x] 10.5 `startMove()` 初始化：从员工现有 `branch`/`team` 回填 region/team/branch 三级

## 11. 前端验证

- [x] 11.1 运行 `cd frontend && npm run build` 确认 TypeScript 类型检查零错误、构建成功
- [x] 11.2 运行 `cd frontend && npm run test` 确认 vitest 无回归
