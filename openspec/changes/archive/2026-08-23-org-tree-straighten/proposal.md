## Why

组织树当前是「双父线 + 平铺 FK」的假树：`Branch` 同时挂 `region` 和 `team` 两条父线，`User` 平铺 `branch/region/team/leader` 四个 FK，`DataScope` 只按 region→branch 一层展开。后果：组织页被迫发明「未分组」虚拟节点、员工归属要在三个字段上手抄同步（移动员工要写 branch+team+region 三处）、region 与 team 不一致靠 serializer 校验兜底、区域负责人的数据范围推导与真实树脱节。总设计书第六节（决策 #12）定案：真实层级为 集团 → 行政大区 → 行政组（分公司唯一父级）→ 分公司 → 行政员工，本轮把模型掰直。

## What Changes

- **Branch.team 升唯一父级（必填）**：`team` 外键改 NOT NULL、`on_delete=PROTECT`；删除 `Branch.region`，区域归属改为派生（`branch.team.region`）。
- **删除 User 平铺 FK**：`User.region` / `User.team` / `User.leader` 三列删除，员工只挂 `branch`；区域/行政组归属全部沿树派生。
- **数据迁移（纯 Python，无数据库特定聚合）**：team 为空的分公司先回填——优先按员工 team 众数（并入原 `assign_branch_team_from_employees` 逻辑），无信号则在所属区域建（或复用）「{区域名}未分组」行政组兜底；回填完成后才加非空约束。删除原回填管理命令（职责并入迁移）。
- **派生值只读暴露保兼容**：`BranchSerializer` 保留只读 `region`（= team.region）；`UserSerializer.region_name` 改由 `branch.team.region` 派生。
- **DataScope 改树遍历**：region 授权 → 旗下行政组 → 全部分公司；team 授权 → 组内分公司；范围统一展开为分公司集合。用户列表查询与 `_validate_in_scope` 去掉 `User.region` 判断。
- **Team 接口正骨**：删除「设组长自动同步 user.team」逻辑；`member_count` 改为组内分公司员工数；删除行政组前若有分公司则拒绝（PROTECT → 400 提示）。
- **分公司按区域筛选改为穿透行政组**：`GET /api/branches?region=X` 过滤 `team__region=X`（参数名不变）。
- **前端组织页**：组织树删除「未分组」节点；分公司表单改选「所属行政组」（不再选区域）；员工表单只选分公司（删区域/行政组下拉）；移动员工三级级联保留但删「未分组」选项、只提交 branch；节点员工归属规则改为「组内分公司员工 ∪ 节点负责人（region.manager / team.leader / branch.manager）」。
- **删除四个无引用的旧组织子页**（PersonnelManager / TeamManager / OrganizationBranch / OrganizationRegion，统一页面上线后已成死代码，且引用被删字段）。

## Capabilities

### New Capabilities
- `org-tree-single-parent`: 组织树唯一父级契约——每节点恰有一个父级（集团→大区→行政组→分公司），员工仅挂分公司，其余归属皆派生；含存量回填与派生规则。

### Modified Capabilities
- `unified-organization-page`: 「分公司隶属行政组（数据模型）」改为 team 必填唯一父级、删 region 列与一致性校验；「左侧组织树」删未分组节点、归属规则改为经 branch/负责人派生；「员工操作（移动）」删未分组选项、team/region 不再同步写入；「分公司 team 数据回填」整体移除（并入迁移）；「顶层集团根/各层级员工不隐藏」措辞改为无平铺 FK 语义。
<!-- management-permissions 不改：其 requirement 为结果级约定（区域授权覆盖旗下全部分公司与行政组），树遍历展开后语义不变，解析算法属实现细节。 -->

## Impact

- **后端模型/迁移**：`apps/organizations/models.py`（Branch）、`apps/users/models.py`（User）+ 两个新迁移（organizations.0007 回填+改约束+删列、users.0006 删三列）。
- **后端逻辑**：`organizations/{serializers,views,filters}.py`、`users/{serializers,views}.py`、`apps/permissions/scope.py`、`core/permissions.py`（DataScopeMixin 文档与 teams 集合语义）。
- **删除**：`organizations/management/commands/assign_branch_team_from_employees.py`。
- **前端**：`views/Organization.vue`、`utils/orgTree.ts`、`types/index.ts`、`api/users.ts` 类型；删除 `views/organization/` 四个旧子页。
- **测试**：`test_organizations.py`、`test_users.py`、`test_user_profile_branch.py`、`test_data_scoping.py`、`test_management_permissions.py`、`test_asset_crud.py`、`test_transfers.py`、`test_import_export.py` 等中 region/team/leader 相关构造与断言。
- **非目标**：supervisor 退役、岗位模板/任命即授权（小案③）；ManagementScope 模型结构不动（仅改解析算法）；`org-teams-tab`/`org-view-all-write-permission` 两份已被统一页面取代的旧基线不在本轮清理。
