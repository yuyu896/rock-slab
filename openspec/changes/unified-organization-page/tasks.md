## 1. 后端：分公司隶属行政组

- [ ] 1.1 `apps/organizations/models.py`：`Branch` 增加 `team = FK('organizations.Team', null=True, blank=True, on_delete=SET_NULL, related_name='branches', verbose_name='所属行政组')`。
- [ ] 1.2 `apps/organizations/serializers.py`：`BranchSerializer.fields` 加 `team`；`validate` 校验若 team 与 region 都提供则 `team.region_id == region_id`，不一致报 400。
- [ ] 1.3 `python manage.py makemigrations organizations` 生成迁移（team 字段 null=True）；`makemigrations --check` 确认无漂移。
- [ ] 1.4 测试：分公司带 team 创建成功、team.region≠branch.region 被拒、team=null 兼容现有数据；`pytest` 全绿。

## 2. 前端骨架 + 左树（新层级）

- [ ] 2.1 `views/Organization.vue` 单页面容器骨架：左侧树区 + 右侧主区（顶部栏/员工栏/列表或编辑），持 `selectedNode`/`editingEmployee`。
- [ ] 2.2 新增 `components/organization/OrgTree.vue`：组织树按 **区域→行政组→分公司** 三层渲染；点击节点 emit `select(node)`。
- [ ] 2.3 `team=null` 的现有分公司在树中归到所在区域下的「未分组」临时分类（管理员后续分配 team）。

## 3. 员工列表 + 顶部操作栏

- [ ] 3.1 新增 `components/organization/EmployeeList.vue`：表格列「姓名(头像)/职务/所属组织(行政组)/账号(手机号)/所属分公司」；emit `edit(employee)`。
- [ ] 3.2 容器在 `selectedNode` 变化时按层级取员工（区域→全部 / 行政组→其下分公司员工 / 分公司→该分公司员工）。
- [ ] 3.3 新增 `components/organization/OrgActionBar.vue`：左=选中组织名+人数；右=按层级动态（区域→编辑区域+新增行政组；行政组→编辑行政组+新增分公司；分公司→编辑分公司）。
- [ ] 3.4 新增下级自动挂载：新增行政组 region=选中区域；新增分公司 team=选中行政组 + region=该行政组.region。

## 4. 员工操作 + 编辑 + 移动

- [ ] 4.1 员工操作栏：「创建员工」（挂当前节点，复用 createUser）、「删除员工」（复用 deleteUser + 确认）。
- [ ] 4.2 新增 `components/organization/EmployeeEditForm.vue`：编辑表单（姓名/手机号/角色/区域/分公司/组/直属上级/状态）+「← 返回列表」。
- [ ] 4.3 点员工 → 容器置 `editingEmployee` → 右侧切换 EmployeeEditForm；返回清空回列表；提交复用 updateUser。
- [ ] 4.4 新增 `components/organization/MoveEmployeeDialog.vue`：选目标分公司 → updateUser 改 branch，并同步 team=目标分公司.team。
- [ ] 4.5 所有组织操作按 `canManageOrganizations`、员工操作按 `canManageUsers` 显隐。

## 5. 删旧 tab + 回归

- [ ] 5.1 删除 `Organization.vue` 中 regions/branches/teams/personnel 四个 tab 的模板/数据/方法/样式（移除 activeTab 多 tab 概念）。
- [ ] 5.2 全量回归：区域/行政组/分公司 增删改、员工增删改/移动、权限、选中态切换、员工编辑返回、迁移后现有分公司 team 分配。
- [ ] 5.3 `npm run build` + `npm run test` 通过；`openspec validate unified-organization-page` 通过。

## 6. 提交与部署

- [ ] 6.1 拆 commit：`feat: 分公司隶属行政组 + 组织架构单页面`（后端模型/迁移 + 前端重构）+ `chore(openspec): unified-organization-page 提案`。
- [ ] 6.2 部署：**前后端都改**，跑 `deploy.sh`（git pull → build backend → migrate → 前端 build → nginx reload）。
- [ ] 6.3 线上验证：迁移执行后，现有分公司 team=null，管理员在 UI 逐步把分公司分配到行政组。
