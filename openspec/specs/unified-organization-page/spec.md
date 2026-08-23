# unified-organization-page Specification

## Purpose
TBD - created by archiving change unified-organization-page. Update Purpose after archive.
## Requirements
### Requirement: 分公司隶属行政组（数据模型）

`Branch` 的 `team` 外键（所属行政组）MUST 为必填且是分公司唯一父级，建立 **区域 → 行政组 → 分公司** 层级；`Branch` MUST NOT 持有独立的 `region` 列，区域归属由 `branch.team.region` 派生并以只读字段暴露。原「team 与 region 一致性校验」随 `region` 列删除而废止（不可能出现跨区域错挂）。

#### Scenario: 分公司带行政组创建

- **WHEN** 创建分公司时指定 team
- **THEN** 分公司 team 保存为该行政组，层级关系正确

#### Scenario: 未指定行政组被拒绝

- **WHEN** 创建分公司时未指定 team
- **THEN** 返回 400 校验错误，分公司不创建

### Requirement: 组织架构单页面（删除多 tab）

组织架构模块 MUST 为**单一页面**，MUST NOT 保留「区域 / 分公司 / 行政组 / 人员管理」的独立 tab。所有操作集中在单页面。

#### Scenario: 单页面无 tab 切换

- **WHEN** 用户进入组织架构
- **THEN** 显示单一页面（左树 + 右主区），无四个独立 tab

### Requirement: 左侧组织树（区域→行政组→分公司）

左侧 MUST 按 **区域 → 行政组 → 分公司** 三层展现组织树；每个分公司必有行政组父级，MUST NOT 出现「未分组」虚拟节点。**员工 MUST NOT 作为树节点出现**（员工在右侧列表呈现）。点击组织节点 MUST 选中，右侧员工列表 MUST 按以下沿树派生的规则显示该节点范围内的员工（节点员工 = 子树分公司挂靠员工 ∪ 子树内全部负责人任命）：

- 分公司节点：`u.branch = 该分公司` ∪ `u = branch.manager`
- 行政组节点：`u.branch ∈ 该组下分公司` ∪ `u ∈ 组内分公司 manager` ∪ `u = team.leader`
- 区域节点：`u.branch ∈ 该区域旗下分公司（经行政组）` ∪ `u ∈ 旗下分公司 manager` ∪ `u ∈ 该区域各组 leader` ∪ `u = region.manager`

#### Scenario: 行政组节点显示组内分公司员工与组长

- **WHEN** 选中某行政组节点
- **THEN** 右侧显示该组全部分公司下的员工，以及 `team.leader`（即使其无分公司挂靠）

#### Scenario: 区域节点显示该区域全员与负责人

- **WHEN** 选中某区域节点
- **THEN** 右侧显示该区域旗下（经行政组）分公司员工，以及区域负责人与各组组长（即使其无分公司挂靠）

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

员工列表上方 MUST 提供「创建 / 移动 / 删除员工」，受 `manage_users` 权限控制。创建默认挂当前节点。**移动员工 MUST 通过 区域 → 行政组 → 分公司 三级级联弹窗选择目标，分公司必选**；行政组下拉列所选区域的真实行政组（无「未分组」选项）；选行政组时分公司下拉只列该组下分公司；**提交 MUST 仅写 branch**（区域/行政组由分公司沿树派生，不再同步写入任何员工字段）。

#### Scenario: 移动弹窗三级级联

- **WHEN** 点击「移动」打开移动弹窗
- **THEN** 弹窗依次提供「区域」「行政组」「分公司」三个下拉（无「未分组」选项）；分公司为必选；切换区域清空行政组与分公司，切换行政组清空分公司

#### Scenario: 移动员工只改分公司

- **WHEN** 确认移动，选中目标分公司
- **THEN** 员工的 `branch` 改为目标分公司，无其他组织字段被写入

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

### Requirement: 顶层集团根（启航集团）

组织树 MUST 有一个顶层虚拟根节点「启航集团」（单一集团，前端虚拟节点，集团名持久化于后端 Company 单例），所有区域挂其下。集团根选中时，右侧员工列表 MUST 显示**所有员工**（含无分公司归属的员工），不得隐藏。

#### Scenario: 集团根显示全员

- **WHEN** 点击「启航集团」根节点
- **THEN** 右侧显示全部员工，含没有任何分公司归属的员工

#### Scenario: 无归属员工在集团根可见

- **WHEN** 员工 `branch` 为空且不担任任何节点负责人
- **THEN** 该员工在「启航集团」根节点的员工列表中可见（不再仅靠搜索）

### Requirement: 各层级员工不隐藏

每个组织节点 MUST 显示其管辖范围内的所有员工，不得因员工缺少更细归属而隐藏。区域节点 MUST 显示沿树落入该区域的员工，以及区域负责人（`region.manager`）与该区域各行政组组长（`team.leader`），即使他们无分公司挂靠。

#### Scenario: 区长在区域节点可见

- **WHEN** 区长（区域负责人）`branch` 为空但为该区域 `manager`
- **THEN** 选中该区域节点时，区长在员工列表中可见

### Requirement: 员工列表按职级排序

员工列表 MUST 按 role 职级从高到低排序（admin > director > manager > supervisor > leader > staff），同职级按姓名升序。集团根节点选中时，无区域归属的高级别账号（行政总监 / 行政经理 / 管理员）因职级高而显示在列表最上层。

#### Scenario: 集团根列表高职级在前

- **WHEN** 点击「启航集团」根节点
- **THEN** 员工列表按职级排序，admin / director / manager 等高职级在前，staff 在后；无区域的高级别账号排在最上层

#### Scenario: 各节点员工均按职级排序

- **WHEN** 选中任意组织节点查看员工列表
- **THEN** 列表按职级排序（排序规则不因节点不同而改变）

### Requirement: 区域节点显示编码

组织树的区域节点 MUST 显示区域编码（`code`），格式如「区域名称（编码）」。

#### Scenario: 区域节点显示 name + code

- **WHEN** 查看组织树
- **THEN** 区域节点显示名称与编码，如「华东区域（HD）」

### Requirement: 集团名可编辑（Company 单例）

集团名 MUST 持久化在后端 `Company` 单例模型（预置「启航集团」），管理员 MUST 能在组织架构页编辑集团名（受 `manage_organizations`），改名 MUST 全局生效（所有用户看到新名）。组织树根节点 MUST 显示当前 `Company.name`。

#### Scenario: 编辑集团名

- **WHEN** 管理员在集团根点击「编辑集团」，输入新名并保存
- **THEN** 集团名更新为 `Company.name`，组织树根节点显示新名，所有用户生效

#### Scenario: 普通用户看到当前集团名

- **WHEN** 任意用户打开组织架构页
- **THEN** 根节点显示后端 `Company` 当前的 `name`

