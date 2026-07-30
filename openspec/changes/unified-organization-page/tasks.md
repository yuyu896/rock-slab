## 1. 后端：分公司隶属行政组

- [x] 1.1 `apps/organizations/models.py`：`Branch` 增加 `team = FK('organizations.Team', null=True, blank=True, on_delete=SET_NULL, related_name='branches', verbose_name='所属行政组')`。
- [x] 1.2 `apps/organizations/serializers.py`：`BranchSerializer.fields` 加 `team`；`validate` 校验若 team 与 region 都提供则 `team.region_id == region_id`，不一致报 400。
- [x] 1.3 `python manage.py makemigrations organizations` 生成迁移（team 字段 null=True）；`makemigrations --check` 确认无漂移。
- [x] 1.4 测试：分公司带 team 创建成功、team.region≠branch.region 被拒、team=null 兼容现有数据；`pytest` 全绿。

## 2. 前端骨架 + 左树（新层级）

- [x] 2.1 `views/Organization.vue` 单页面容器骨架：左侧树区 + 右侧主区（顶部栏/员工栏/列表或编辑），持 `selectedNode`/`editingEmployee`。
- [x] 2.2 组织树按 **区域→行政组→分公司** 三层渲染；点击节点选中（实现内联于 `Organization.vue`，未拆独立 `OrgTree.vue` 组件）。
- [x] 2.3 `team=null` 的现有分公司在树中归到所在区域下的「未分组」临时分类（管理员后续分配 team）。

## 3. 员工列表 + 顶部操作栏

- [x] 3.1 员工表格列「姓名/职务/所属组织(行政组)/账号(手机号)/所属分公司」；点击行→编辑（内联于 `Organization.vue`）。
- [x] 3.2 容器在 `selectedNode` 变化时按层级取员工（区域→全部 / 行政组→其下分公司员工 / 分公司→该分公司员工）。
- [x] 3.3 顶部操作栏：左=选中组织名+人数；右=按层级动态（区域→编辑区域+新增行政组；行政组→编辑行政组+新增分公司；分公司→编辑分公司）（内联）。
- [x] 3.4 新增下级自动挂载：新增行政组 region=选中区域；新增分公司 team=选中行政组 + region=该行政组.region。

## 4. 员工操作 + 编辑 + 移动

- [x] 4.1 员工操作栏：「创建员工」（挂当前节点，复用 createUser）、「删除员工」（复用 deleteUser + 确认）。
- [x] 4.2 员工编辑表单（姓名/手机号/角色/区域/分公司/组/状态）+「← 返回列表」（右侧切换页面，内联）。
- [x] 4.3 点员工 → 容器置 `editingEmployee` → 右侧切换编辑表单；返回清空回列表；提交复用 updateUser。
- [x] 4.4 移动员工弹窗：选目标区域→目标分公司 → updateUser 改 branch，并同步 team=目标分公司.team、region=目标分公司.region（内联于 `Organization.vue`）。
- [x] 4.5 所有组织操作按 `canManageOrganizations`、员工操作按 `canManageUsers` 显隐。

## 5. 删旧 tab + 回归

- [x] 5.1 删除 `Organization.vue` 中 regions/branches/teams/personnel 四个 tab 的模板/数据/方法/样式（移除 activeTab 多 tab 概念）。
- [x] 5.2 全量回归：区域/行政组/分公司 增删改、员工增删改/移动、权限、选中态切换、员工编辑返回。
- [x] 5.3 `npm run build` + `npm run test` 通过；`openspec validate unified-organization-page` 通过。

## 6. 提交与部署

- [x] 6.1 拆 commit：`feat: 组织架构页 - 移动员工功能`（前端）+ `chore(openspec): unified-organization-page 勾选已完成任务`。（第 1-2 阶段已于 `cf60279` 合并；本 commit 补齐第 3 阶段移动员工）
- [ ] 6.2 部署：**本次仅前端改动**（无后端模型/迁移变化），跑 `deploy.sh`（git pull → 前端 build → nginx reload）。
- [ ] 6.3 线上验证：登录后进入组织架构页，对员工点「移动」→ 选目标分公司 → 确认员工分公司/行政组随之更新。
