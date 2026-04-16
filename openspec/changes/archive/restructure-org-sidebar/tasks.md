## 1. 后端 Team 模型与迁移

- [x] 1.1 在 `organizations` app 的 `models.py` 中新增 `Team` 模型：`name`(CharField), `region`(FK→Region), `leader`(FK→User, null/blank), `status`(CharField choices), `created_at`, `updated_at`
- [x] 1.2 User 模型新增 `team` FK 字段（FK→Team, null=True, blank=True, related_name='members'）
- [x] 1.3 执行数据库迁移 `python manage.py makemigrations organizations` 和 `python manage.py migrate`

## 2. 后端 Team API

- [x] 2.1 新增 `TeamSerializer`：字段包含 id, name, region, region_name, leader, leader_name, member_count, status, created_at, updated_at
- [x] 2.2 新增 `TeamViewSet`（ModelViewSet），注册到 organizations app 的 urls.py，路径 `/api/teams/`，权限要求 admin 或 manager
- [x] 2.3 TeamViewSet 的 `perform_create` / `perform_update` 中，若设置了 leader，自动将该 user 的 `team` 字段指向此 Team
- [x] 2.4 TeamViewSet 的 `perform_destroy` 中，将所有成员的 `team` 字段置为 null
- [x] 2.5 UserSerializer 的 fields 列表新增 `team` 字段

## 3. 后端 User 过滤器扩展

- [x] 3.1 UserFilterSet 新增 `team` 过滤器（`field_name='team_id'`），支持 `GET /api/users/?team=<id>` 查询

## 4. 前端类型与 API

- [x] 4.1 `types/index.ts` 新增 `Team` 接口定义（id, name, region, leader, status, memberCount 等）
- [x] 4.2 `User` 接口新增 `team?: string` 字段
- [x] 4.3 新增 `api/teams.ts`：`getTeams`, `getTeam`, `createTeam`, `updateTeam`, `deleteTeam` 函数

## 5. 前端侧边栏树重构

- [x] 5.1 重写 `buildOrgTree` 函数（替代原 `buildUserTree`），按新层级构建：集团根节点 → manager 用户 + 区域列表 → supervisor 用户 + 行政组列表 → leader + staff 用户
- [x] 5.2 定义新的树节点类型（OrgTreeNode），支持 nodeType: 'group' | 'region' | 'team' | 'person' 等类型
- [x] 5.3 侧边栏模板重写：第一层固定显示「集团」，第二层渲染 manager 和区域，第三层渲染 supervisor 和组，第四层渲染组长和组员
- [x] 5.4 点击不同类型节点（区域/组/人员）时，右侧面板切换显示对应详情内容

## 6. 前端行政组管理 UI

- [x] 6.1 组织架构标签页中，区域节点下新增「添加行政组」按钮/入口
- [x] 6.2 新增/编辑行政组的弹窗表单：组名（必填）、所属区域（自动填充）、组长（下拉选择）
- [x] 6.3 删除行政组时，若有成员则提示确认信息，确认后调用 deleteTeam API
- [x] 6.4 组详情面板：显示组名、区域、组长、成员列表

## 7. 前端人员管理适配

- [x] 7.1 人员管理标签页表格新增「所属组」列，显示 `user.team` 对应的组名
- [x] 7.2 新增/编辑人员弹窗新增「所属组」下拉选择，选择区域后联动筛选该区域下的组
- [x] 7.3 人员筛选器新增「所属组」下拉筛选

## 8. 验证

- [x] 8.1 确认侧边栏层级结构正确：集团→行政经理+区域→行政主管+行政组→组长+组员
- [x] 8.2 确认行政组 CRUD 操作正常：创建、编辑、删除
- [x] 8.3 确认人员创建时可选所属组，组下拉按区域联动筛选
- [x] 8.4 确认删除组后成员的 team 字段正确置空
