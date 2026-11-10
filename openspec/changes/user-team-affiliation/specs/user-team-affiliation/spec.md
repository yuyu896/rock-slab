## ADDED Requirements

### Requirement: User.team 可空外键

`User` 模型 MUST 新增 `team` 可空外键（→ `organizations.Team`，`on_delete=models.SET_NULL`，`related_name='users'`）。`team` 表示员工直接归属行政组（不隶属任何分公司时使用）。

#### Scenario: 创建直接归属行政组的员工

- **WHEN** 创建员工时未指定 `branch`，指定了 `team`
- **THEN** 员工 `branch` 为 null，`team` 保存为该行政组

#### Scenario: 创建分公司员工自动置空 team

- **WHEN** 创建员工时指定了 `branch`
- **THEN** `team` 强制为 null（即使请求体中传了 team 值），员工区域/行政组由 `branch.team` 派生

#### Scenario: 移动到分公司时清空 team

- **WHEN** 编辑员工时 `branch` 从空改为某分公司
- **THEN** `team` 置为 null

#### Scenario: 移出分公司时设置 team

- **WHEN** 编辑员工时 `branch` 从某分公司改为空，且指定了 `team`
- **THEN** `branch` 置为 null，`team` 保存为指定行政组

### Requirement: 默认数据范围按 team 兜底

无显式 `ManagementScope` 授权的员工，`resolve_user_scope` 的默认范围 MUST 在 `branch` 为空且 `team` 有值时，将该 `team` 下所有分公司 id 纳入 `Scope.branches`，使员工可见并操作 team 下的分公司业务数据。

#### Scenario: 仅归属行政组的员工可见组内分公司

- **WHEN** 员工 `branch` 为空、`team` 指向某行政组，且该行政组下有分公司
- **THEN** 该员工的默认数据范围 `Scope.branches` 包含该行政组下所有分公司 id，`Scope.all` 为 false

#### Scenario: 行政组下无分公司时范围仍为空

- **WHEN** 员工 `branch` 为空、`team` 指向某行政组，但该行政组下无任何分公司
- **THEN** 该员工默认数据范围 `Scope.branches` 为空集（无可见分公司）

### Requirement: 范围内用户可见性含 team 路径

`UserViewSet._get_user_queryset` 的范围过滤 MUST 支持仅归属行政组的员工：`branch` 为空、`team` 有值且其对应分公司落在操作者范围内时，该员工可见。

#### Scenario: 操作者可见 team 直属员工

- **WHEN** 操作者数据范围覆盖某 team 下全部分公司，目标员工 `branch` 为空、`team` 为该行政组
- **THEN** 目标员工出现在操作者的用户列表中

### Requirement: 编辑/删除范围校验含 team 路径

`UserViewSet._validate_in_scope` 和 `_validate_delete_scope` MUST 在 target 员工 `branch` 为空时，回退判断其 `team` 下分公司是否落在操作者范围内。

#### Scenario: 移动仅归属行政组的员工

- **WHEN** 操作者范围覆盖目标员工 `team` 下的分公司，且目标员工 `branch` 为空、`team` 有值
- **THEN** 允许操作者编辑/移动该员工

#### Scenario: 拒绝范围外 team 员工操作

- **WHEN** 目标员工 `branch` 为空、`team` 有值，但操作者范围不覆盖该 team 的任何分公司
- **THEN** 返回校验错误，拒绝编辑/删除

### Requirement: UserSerializer 回填 team 信息

`UserSerializer` MUST 回填 `team`（uuid）和 `teamName`（行政组名称）只读字段。写入时校验 branch/team 互斥：`branch` 非空则忽略并清空 `team`。

#### Scenario: 序列化回填 teamName

- **WHEN** 员工 `branch` 为空、`team` 指向「华东行政组」
- **THEN** 序列化结果含 `team: <uuid>` 和 `teamName: "华东行政组"`

#### Scenario: 分公司员工 teamName 为空

- **WHEN** 员工有 `branch` 分公司归属
- **THEN** 序列化结果 `team` 为 null，`teamName` 为空字符串

### Requirement: 前端 User 类型含 team 字段

`frontend/src/types/index.ts` 的 `User` 接口 MUST 新增 `team?: string | null` 和 `teamName?: string`。

#### Scenario: 类型定义

- **WHEN** 前端定义 User 类型
- **THEN** User 接口含 `team?: string | null` 和 `teamName?: string` 字段

### Requirement: 按 team 过滤用户

`UserFilterSet` MUST 支持 `team` 查询参数，过滤 `team` 等于指定 id 的员工。

#### Scenario: 按 team 过滤

- **WHEN** 请求 `GET /api/users/?team=<uuid>`
- **THEN** 返回 `team` 为该 id 的员工列表
