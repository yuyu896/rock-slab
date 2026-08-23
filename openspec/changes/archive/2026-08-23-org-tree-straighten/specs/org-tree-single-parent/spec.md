## ADDED Requirements

### Requirement: 组织树唯一父级（数据模型）
组织树每个节点 MUST 恰有一个父级，层级为 集团（单例）→ 区域（Region）→ 行政组（Team）→ 分公司（Branch）→ 员工（User）。`Branch.team` MUST 为必填外键且是分公司的唯一父级（`NOT NULL`）；`Branch` MUST NOT 持有 `region` 列（区域归属由 `branch.team.region` 派生）。`User` MUST 仅通过 `branch` 外键挂靠组织，MUST NOT 持有 `region` / `team` / `leader` 平铺外键。

#### Scenario: 创建分公司必须指定行政组
- **WHEN** 创建分公司时未提供 team
- **THEN** 返回 400 校验错误，分公司不创建

#### Scenario: 员工归属只能写分公司
- **WHEN** 创建/编辑/移动员工
- **THEN** 组织归属仅接受 branch 字段；区域与行政组由 branch 沿树派生，不接受单独写入

### Requirement: 存量分公司 team 回填（数据迁移）
系统 MUST 提供数据迁移为存量 `team` 为空的分公司补齐行政组，回填完成后方可施加非空约束。回填规则（纯 Python，MUST NOT 使用数据库特定聚合）：优先取该分公司员工 `team` 的众数；无员工或员工均无 team 的分公司，挂到其所属区域的「{区域名}未分组」行政组（不存在则创建）。迁移 MUST 输出回填清单日志。

#### Scenario: 员工众数回填
- **WHEN** 某分公司 team 为空，其多数员工的 team 为行政组 T
- **THEN** 迁移将该分公司的 team 置为 T

#### Scenario: 无信号兜底组
- **WHEN** 某分公司 team 为空且无员工或员工均无 team，其所属区域为 R
- **THEN** 迁移在区域 R 下创建（或复用）名为「{R 名}未分组」的行政组，并将该分公司挂入

#### Scenario: 迁移后约束生效
- **WHEN** 回填迁移完成
- **THEN** `Branch.team` 非空约束生效，不存在 team 为空的分公司

### Requirement: 区域归属为派生值
分公司的区域归属 MUST 由 `branch.team.region` 派生。分公司列表接口 MUST 支持按区域筛选（`?region=<id>` 过滤 `team__region`），并在响应中暴露只读派生字段 `region`（= team.region id）；用户接口的 `region_name` MUST 由 `branch.team.region.name` 派生。

#### Scenario: 按区域筛选分公司穿透行政组
- **WHEN** 以 `?region=R` 请求分公司列表
- **THEN** 返回 R 下所有行政组的全部分公司

#### Scenario: 用户区域名随分公司派生
- **WHEN** 员工挂靠分公司 B（B.team.region = R）
- **THEN** 该员工的 `region_name` 为 R 的名称，无分公司则为空

### Requirement: 节点员工范围沿树派生（含负责人）
组织节点的员工范围 MUST 沿树派生，不依赖员工平铺字段。统一规则：节点员工 = 子树分公司挂靠员工 ∪ 子树内全部负责人任命：
- 分公司节点：`u.branch = 该分公司` ∪ `u = branch.manager`
- 行政组节点：`u.branch ∈ 组内分公司` ∪ `u ∈ 组内分公司 manager` ∪ `u = team.leader`
- 区域节点：`u.branch ∈ 区域旗下分公司（经行政组）` ∪ `u ∈ 旗下分公司 manager` ∪ `u ∈ 该区域各组 leader` ∪ `u = region.manager`
- 集团根：全部员工（含无任何归属的员工）

无分公司挂靠的负责人（区域 manager / 行政组 leader / 分公司 manager）MUST 仍在其管辖节点可见。

#### Scenario: 区长在区域节点可见
- **WHEN** 区域负责人 `branch` 为空但为该区域 `manager`
- **THEN** 选中该区域节点时负责人出现在员工列表

#### Scenario: 组长在行政组节点可见
- **WHEN** 行政组长 `branch` 为空但为该组 `leader`
- **THEN** 选中该行政组节点时组长出现在员工列表

### Requirement: 行政组删除保护
删除仍有分公司的行政组 MUST 被拒绝并返回明确提示；删除空行政组 MUST 正常成功。系统 MUST NOT 因删除行政组而级联删除或静默脱挂其分公司。

#### Scenario: 删除有分公司的行政组被拒
- **WHEN** 删除的行政组下存在分公司
- **THEN** 返回 400 提示先处理旗下分公司，行政组与分公司均不变

#### Scenario: 删除空行政组成功
- **WHEN** 删除的行政组下无分公司
- **THEN** 删除成功

### Requirement: 组长指派不再回写员工字段
设置/变更行政组组长（`team.leader`）MUST 仅写入树节点字段，MUST NOT 回写员工的任何组织归属字段。

#### Scenario: 设置组长不改动该员工归属
- **WHEN** 将员工 X 设为行政组 T 的组长
- **THEN** X 的 branch 保持原值不变
