# unified-organization-page Specification

## Purpose
TBD - created by archiving change unified-organization-page. Update Purpose after archive.
## Requirements
### Requirement: 分公司隶属行政组（数据模型）

`Branch` MUST 增加 `team` 外键（所属行政组，允许为空），分公司隶属行政组，建立 **区域 → 行政组 → 分公司** 层级。`Branch.team.region` MUST 与 `Branch.region` 一致（serializer 校验，防止跨区域错挂）。

#### Scenario: 分公司带行政组创建

- **WHEN** 创建分公司时指定 team
- **THEN** 分公司 team 保存为该行政组，层级关系正确

#### Scenario: team 与 region 一致性校验

- **WHEN** 创建/编辑分公司时 team 所属区域 != 分公司所属区域
- **THEN** 返回 400 拒绝，提示区域不一致

### Requirement: 组织架构单页面（删除多 tab）

组织架构模块 MUST 为**单一页面**，MUST NOT 保留「区域 / 分公司 / 行政组 / 人员管理」的独立 tab。所有操作集中在单页面。

#### Scenario: 单页面无 tab 切换

- **WHEN** 用户进入组织架构
- **THEN** 显示单一页面（左树 + 右主区），无四个独立 tab

### Requirement: 左侧组织树（区域→行政组→分公司）

左侧 MUST 按 **区域 → 行政组 → 分公司** 三层展现组织树；区域下 `team=null` 的分公司 MUST 聚合为「未分组」节点（置于该区域的行政组之后）。**员工 MUST NOT 作为树节点出现**（员工在右侧列表呈现）。点击组织节点 MUST 选中，右侧员工列表 MUST 按以下归属规则显示该节点范围内的员工：

- 分公司节点：`u.branch = 该分公司`
- 行政组节点：`u.branch ∈ 该组下分公司` **∪** `u.team = 该组 且 u.branch=null`
- 未分组节点：`u.branch ∈ 该区域 team=null 的分公司`
- 区域节点：`u.region = 该区域`

「未分组」节点选中时 MUST 显示其下员工，不得因节点是虚拟节点（`rawId` 空）而返回空列表。

#### Scenario: 点击未分组节点显示员工

- **WHEN** 点击某区域的「未分组」节点（聚合该区域 `team=null` 的分公司）
- **THEN** 右侧显示这些未分组分公司下的所有员工，列表非空（若确无员工则显示空状态）

#### Scenario: 无分公司但有行政组的员工在组节点可见

- **WHEN** 员工 `branch=null` 且 `team=某行政组`，选中该行政组节点
- **THEN** 右侧员工列表包含该员工（按最具体归属呈现）

#### Scenario: 区域节点显示该区域全员

- **WHEN** 选中某区域节点
- **THEN** 右侧显示 `u.region = 该区域` 的所有员工（含无分公司、无行政组但有所属区域的员工）

### Requirement: 员工列表

选中节点后，右侧 MUST 显示员工列表，列含：**姓名、职务、所属组织（行政组）、账号（手机号）、所属分公司**。

#### Scenario: 员工列表展示

- **WHEN** 选中某节点
- **THEN** 列表显示对应员工，每行含姓名/职务/所属组织/账号/所属分公司

### Requirement: 顶部组织操作栏（按层级动态）

顶部栏 MUST：左 = 选中组织名称 + 人数；右 = **按层级动态**操作（受 `manage_organizations` 权限控制）：
- 选中**区域** → 编辑区域 + 新增行政组
- 选中**行政组** → 编辑行政组 + 新增分公司
- 选中**分公司** → 编辑分公司

新增下级时自动挂载到当前节点（区域/行政组预填）。

#### Scenario: 按层级显示操作

- **WHEN** 选中行政组
- **THEN** 顶部右侧显示「编辑行政组」「新增分公司」（新分公司 team=该行政组）

### Requirement: 员工操作（创建 / 移动 / 删除）

员工列表上方 MUST 提供「创建 / 移动 / 删除员工」，受 `manage_users` 权限控制。创建默认挂当前节点；**移动员工 MUST 通过 区域 → 行政组 → 分公司 三级级联弹窗选择目标，分公司必选**；行政组下拉列所选区域的真实行政组 + 「未分组」选项；选真实行政组时分公司下拉只列该组下分公司，选「未分组」时列该区域 `team=null` 的分公司；最终 `team`/`region` 跟随所选分公司同步（`team=目标分公司.team`，`region=目标分公司.region`）。

#### Scenario: 移动弹窗三级级联

- **WHEN** 点击「移动」打开移动弹窗
- **THEN** 弹窗依次提供「区域」「行政组（真实行政组 + 未分组选项）」「分公司」三个下拉；分公司为必选；切换区域清空行政组与分公司，切换行政组清空分公司；选真实行政组时分公司下拉列该组分公司，选「未分组」时列该区域 `team=null` 的分公司

#### Scenario: 移动员工同步 team 与 region

- **WHEN** 确认移动，选中目标分公司
- **THEN** 员工的 `branch` 改为目标分公司，`team` 同步为目标分公司的行政组，`region` 同步为目标分公司的区域

#### Scenario: 未分组员工可移出

- **WHEN** 选中「未分组」节点，对其中员工点击「移动」，选择某真实行政组下的分公司并确认
- **THEN** 员工从「未分组」移出，归属到所选分公司及其行政组、区域

#### Scenario: 移动到未分组分公司

- **WHEN** 移动弹窗选「未分组」行政组，选某 `team=null` 的分公司并确认
- **THEN** 员工移到该分公司，`team` 同步为空（分公司无行政组）

### Requirement: 员工编辑（右侧切换表单）

点击员工 MUST 在右侧切换为编辑表单（不离开页面），带「← 返回列表」。返回后回列表，选中节点不丢。

#### Scenario: 点击员工切换编辑

- **WHEN** 点击员工列表中某员工
- **THEN** 右侧切换为该员工编辑表单；返回回列表，仍停留原选中节点

### Requirement: 分公司编码唯一校验

创建/编辑分公司时，若 `code` 已被**其他**分公司占用，MUST 返回 400 校验错误（提示编码已存在），MUST NOT 触发 500。编辑分公司时保留自身当前 `code` MUST 通过校验。

#### Scenario: 创建已存在 code 的分公司

- **WHEN** 创建分公司，`code` 已被其他分公司占用
- **THEN** 返回 400，提示编码已存在，不创建分公司

#### Scenario: 编辑分公司保留自身 code

- **WHEN** 编辑分公司，`code` 与自身当前 code 相同
- **THEN** 通过校验，正常保存

### Requirement: 分公司 team 数据回填

系统 MUST 提供管理命令，根据员工的 `team` 推断并回填分公司的 `team`，且支持 `--dry-run` 预览（不写库）。回填规则：取该分公司员工 `team` 的众数；无员工或员工均无 `team` 的分公司保持 `null`。

#### Scenario: dry-run 预览回填

- **WHEN** 运行 `assign_branch_team_from_employees --dry-run`
- **THEN** 输出每个分公司将被分配的 team（员工 team 众数），不修改数据库

#### Scenario: 执行回填

- **WHEN** 运行命令（不带 `--dry-run`）
- **THEN** 有众数 team 的分公司被赋值；无员工 / 员工均无 team 的分公司保持 `null`

### Requirement: 顶层集团根（启航集团）

组织树 MUST 有一个顶层虚拟根节点「启航集团」（单一集团，前端虚拟节点，无后端模型），所有区域挂其下。集团根选中时，右侧员工列表 MUST 显示**所有员工**（含 `branch`/`team`/`region` 全空的员工），不得隐藏。

#### Scenario: 集团根显示全员

- **WHEN** 点击「启航集团」根节点
- **THEN** 右侧显示全部员工，含没有任何组织归属的员工

#### Scenario: 全无归属员工在集团根可见

- **WHEN** 员工 `branch`/`team`/`region` 均为空
- **THEN** 该员工在「启航集团」根节点的员工列表中可见（不再仅靠搜索）

### Requirement: 各层级员工不隐藏

每个组织节点 MUST 显示其管辖范围内的所有员工，不得因员工缺少更细归属而隐藏。区域节点 MUST 显示 `u.region = 该区域` 的所有员工（含区长等无分公司 / 行政组归属的负责人）。

#### Scenario: 区长在区域节点可见

- **WHEN** 区长（区域负责人）`branch`/`team` 为空但 `region = 某区域`
- **THEN** 选中该区域节点时，区长在员工列表中可见

