## Context

现有数据模型：`Region`（区域）下，`Branch`（分公司）和 `Team`（行政组）**并列**（都 `FK(Region)`），无相互隶属。员工 `User` 同时有 `branch`/`team`/`region`。

本次按产品决策建立 **区域 → 行政组 → 分公司** 层级：分公司隶属行政组（`Branch.team = FK(Team)`）。前端整合为单页面，左树按新层级，右侧员工列表 + 统一操作。

后端 API 齐全（users/regions/branches/teams CRUD），需补 Branch 的 team 字段。

## Goals / Non-Goals

**Goals:**
- 后端：分公司隶属行政组（Branch.team FK），层级 Region→Team→Branch。
- 前端：单页面（左树新层级 + 右员工列表 + 统一操作栏），删除 4 个独立 tab。

**Non-Goals:**
- 不改 Region / Team 模型本身（Team 仍属 Region）。
- 不改主侧边栏、不改员工-分公司/团队的归属语义（员工仍属一个分公司 + 一个行政组）。
- 不自动回填现有分公司的 team（无历史数据，由管理员 UI 分配）。
- 不做拖拽改层级。

## Decisions

### D1. 数据模型：Branch 增加 `team` 外键
**选择**：`Branch.team = FK('organizations.Team', null=True, blank=True, on_delete=SET_NULL)`。分公司隶属行政组；允许 null（兼容现有数据 + 行政组可能不辖所有分公司）。
**理由**：null=True 避免迁移强制回填（无历史归属）；SET_NULL 在行政组删除时分公司不级联删（保留分公司，team 置空）。
**一致性校验**：Branch.team 的 region 应与 Branch.region 一致（同一区域下）——在 serializer.validate 校验。

### D2. 迁移策略
**选择**：新增 `team` 字段（null=True）的迁移；**不回填**（现有分公司 team=null）。上线后管理员在 UI 把现有分公司分配到行政组。
**理由**：无历史「分公司属哪个行政组」的数据，自动回填无依据；null 允许渐进分配。

### D3. API：Branch serializer 加 team
**选择**：`BranchSerializer.fields` 加 `team`；`validate` 校验 team.region == region（若都提供）。Branch 创建/编辑支持 team。其他（Region/Team/User）不变。

### D4. 页面结构：左树（新层级）+ 右主区
左侧组织树按 **区域 → 行政组 → 分公司** 三层（叶子=分公司）。右侧主区：
1. 顶部组织操作栏（选中组织名+人数 + 按层级操作）
2. 员工操作栏（创建/移动/删除）+ 员工列表
3. 员工编辑表单（切换）

选中节点取员工范围：
- 选中分公司 → 该分公司员工
- 选中行政组 → 该组下所有分公司员工
- 选中区域 → 该区域所有员工

### D5. 员工列表：表格
列：姓名(头像)、职务、所属组织(行政组)、账号(手机号)、所属分公司。点击行→编辑。

### D6. 员工编辑：右侧切换表单（带返回）
复用现有用户表单字段（姓名/手机号/角色/区域/分公司/组/直属上级/状态）。返回回列表，选中节点不丢。

### D7. 顶部组织操作：按层级动态
- 选中**区域** → [编辑区域] [新增行政组]（行政组 region=该区域）
- 选中**行政组** → [编辑行政组] [新增分公司]（分公司 team=该行政组，region=该行政组的 region）
- 选中**分公司** → [编辑分公司]
受 `canManageOrganizations` 权限控制。

### D8. 移动员工：弹窗选目标
「移动员工」→ 弹窗选目标分公司（+行政组）→ updateUser 改 branch（及 team）。先单个。限 `manage_users` + 目标在授权范围。

### D9. 组件拆分（控制单文件体量）
Organization.vue 拆出：`OrgTree.vue`（左树新层级）、`EmployeeList.vue`、`EmployeeEditForm.vue`、`MoveEmployeeDialog.vue`、`OrgActionBar.vue`。容器编排 + 持 `selectedNode`/`editingEmployee` 状态。

## Risks / Trade-offs

- **[数据模型改动 + 迁移]** → Mitigation：team=null=True 无破坏性；迁移在部署时 `deploy.sh migrate` 执行；现有分公司 team=null，UI 渐进分配。
- **[现有分公司 team=null 的展示]** → Mitigation：树中 team=null 的分公司挂在「未分组」临时节点下，或挂在区域下；管理员逐步分配。
- **[大重构 2000+ 行]** → Mitigation：分阶段（后端模型/迁移 → 前端骨架+树 → 列表 → 操作栏 → 编辑 → 移动 → 删旧 tab）。
- **[层级一致性]** → Branch.team.region 须 == Branch.region，serializer 校验，防数据错乱。

## Migration Plan

含后端迁移，需 `deploy.sh`（非仅前端）。分阶段：
1. **后端**：Branch 加 team FK + 迁移 + serializer + 校验 + 测试。
2. **前端骨架**：单页面容器 + 左树（新层级）+ 选中态。
3. **员工列表** + 顶部操作栏（按层级）。
4. **员工操作 + 编辑** + 移动员工。
5. **删旧 tab** + 回归。
- 部署：`deploy.sh`（migrate + build backend + 前端 build + nginx reload）。
- **回滚**：后端迁移 reversible（reverse 去掉 team 字段）；前端 git revert。

## Open Questions

1. **现有分公司 team=null 在树中的展示**：挂「未分组」节点 / 挂区域下 / 强制分配？—— *倾向：挂区域下「未分组」临时分类，管理员逐步分配。*
2. **移动员工是否同时改 team**：移动到新分公司时，team 是否跟随分公司的 team？—— *倾向：是，移动员工改 branch 时自动同步 team = branch.team。*
3. **员工列表「所属组织」列**：显示行政组名还是分公司名？—— *倾向：行政组（Team），「所属分公司」列单独显示分公司。*
