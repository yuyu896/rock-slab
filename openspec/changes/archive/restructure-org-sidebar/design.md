## Context

当前组织架构侧边栏通过 User 模型的 `leader` 自引用 FK 构建人员树，渲染为固定 4 层嵌套的扁平树。区域(Region)和分公司(Branch) 仅作为用户元数据字段，不参与树层级。用户需要侧边栏展示真实的行政架构层级：集团→区域→组→人员。

现有数据模型：
- User: `role`, `region`(FK→Region), `branch`(FK→Branch), `leader`(FK→User), `avatar`
- Region: `name`, `code`, `manager`(FK→User)
- Branch: `name`, `code`, `region`(FK→Region), `manager`(FK→User)
- 无「组」实体

## Goals / Non-Goals

**Goals:**
- 新增 Team（行政组）模型，归属于区域，包含组长和组员
- 侧边栏重构为：集团（固定顶级）→ 行政经理 + 区域 → 行政主管 + 行政组 → 行政组长和组员
- 人员详情面板适配新的层级结构
- 保持区域管理、分公司管理、人员管理 CRUD 功能不变

**Non-Goals:**
- 不改动权限系统（IsRoleMin 等）
- 不改动分公司管理逻辑
- 不改动资产、盘点、报表等模块
- 不实现动态无限层级递归组件（仍使用固定层级渲染）

## Decisions

### 1. Team 模型放在 organizations app

Team 归属于区域，与 Region/Branch 同属组织结构，放在 `organizations` app 而非新建 app。

**备选**: 新建 `teams` app → 拒绝，因为 Team 是组织架构的一部分，体量小无需独立 app。

### 2. Team 模型字段设计

```
Team:
  name: CharField       # 组名，如"行政一组"
  region: FK→Region     # 所属区域（必填）
  leader: FK→User       # 组长（可选，role=leader）
  status: CharField     # active/inactive
```

User 模型新增 `team: FK→Team`（可空），组员通过 `user.team` 关联到组。

**备选**: Team 与 User 多对多 → 拒绝，一个员工只属于一个组，FK 即可。

### 3. 侧边栏层级树构建逻辑

不再使用 `leader` 自引用构建树，改用以下规则：
1. **集团**：固定顶级节点，显示为根
2. **第二层**：所有 `role=manager` 的用户 + 所有 Region
3. **第三层**：Region 下展示 `role=supervisor` 的用户（`user.region=region.id`）+ 该 Region 下的所有 Team
4. **第四层**：Team 下展示 `role=leader` 的组长 + `role=staff` 的组员（`user.team=team.id`）
5. 无 Team 的 supervisor 下属 staff 也直接挂在 supervisor 下

### 4. 侧边栏交互保持现有模式

选中节点后右侧展示详情面板，复用现有的详情面板 UI 结构。点击组/区域/人员节点分别展示对应详情。

## Risks / Trade-offs

- **[数据迁移]** 现有 leader 关系的用户需要分配到对应的 Team → 需要提供迁移方案或手动调整
- **[团队组长冗余]** Team.leader FK 与 User.leader FK 可能冲突 → 以 Team.leader 为权威来源，User.leader 保留但不用于树构建
- **[固定层级]** 4 层固定渲染无法支持更深层级 → 当前业务需求不超过 4 层，可接受；未来需要时可改为递归组件
