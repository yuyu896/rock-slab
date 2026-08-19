# management-permissions Specification

## Purpose
TBD - created by archiving change decouple-management-permissions. Update Purpose after archive.
## Requirements
### Requirement: 系统必须支持按组织节点授予管理权限

系统 MUST 提供组织节点维度的管理授权，可为任意非 admin 员工授予管理某些大区、分公司、行政组或**整个组织架构（全部数据）**的权限；授权 MUST 可叠加（一个员工可持有多条授权，范围取并集）。`is_all_data`（全部数据）授权为特殊类型：单条即覆盖全部组织节点（含未来新增节点），每用户至多一条，且与具体节点授权互斥。

#### Scenario: 授予大区管理权

- **WHEN** 管理员为员工 A 授予"管理华东大区"的组织节点授权
- **THEN** 系统 MUST 存储 A 对该大区的管理授权
- **AND** A 的数据范围 MUST 包含该大区旗下全部分公司与行政组

#### Scenario: 授予单一行政组管理权

- **WHEN** 管理员为一位行政主管授予"仅管理行政组 X"的授权（该主管职位仍为 supervisor）
- **THEN** 该主管的数据范围 MUST 仅收窄至行政组 X
- **AND** MUST NOT 因其职位为 supervisor 而扩展到整个大区

#### Scenario: 授予全部数据管理权

- **WHEN** 管理员为非 admin 员工 B 授予"整个组织架构（全部数据）"授权（`is_all_data=True`）
- **THEN** 系统 MUST 存储 B 的全局授权
- **AND** B 的数据范围 MUST 等价于全部组织数据（与 admin 数据范围一致）
- **AND** 该全局授权 MUST 覆盖未来新增的大区 / 分公司 / 行政组，无需再次授权

#### Scenario: 全部数据与具体节点互斥

- **WHEN** 尝试创建一条同时标记 `is_all_data=True` 又指定了 region/branch/team 的授权
- **THEN** 系统 MUST 拒绝该校验
- **AND** 每个用户 MUST 至多存在一条 `is_all_data=True` 授权

#### Scenario: 跨组织授权叠加

- **WHEN** 员工 C 同时被授予分公司 F1 与行政组 T2 的管理权
- **THEN** C 的数据范围 MUST 为 F1 全部数据与 T2 数据的并集

### Requirement: 系统必须支持按业务操作授予管理权限

系统 MUST 提供业务操作维度的授权，可为员工授予具体的业务操作权限（如审批采购、管理用户、管理品目）；接口级权限 MUST 基于员工是否持有对应操作授权来判断，而非职位等级。**前端写操作入口 MUST 按对应操作授权控制可见性**——持有授权或 admin 才显示写入口，无授权用户仅见只读视图。

#### Scenario: 持有操作授权方可执行

- **WHEN** 员工 C 被授予 `approve_transfer` 操作授权
- **THEN** C 调用资产调拨审批接口时 MUST 被放行
- **AND** 未被授予该操作的员工 D（非 admin）调用同一接口 MUST 被拒绝（403）

#### Scenario: 接口权限不再依赖职位等级

- **WHEN** 一位 `staff` 职位的员工被授予某业务操作授权
- **THEN** 该员工执行该操作时 MUST 被放行
- **AND** 系统 MUST NOT 因其职位等级为 staff 而拒绝

#### Scenario: 品目写入口按授权可见

- **WHEN** 一个未持有 `manage_categories` 授权的非 admin 用户访问品目模块
- **THEN** 品目列表页 MUST NOT 显示新增 / 编辑 / 删除 / 导入入口
- **AND** 该用户 MUST 仅能查看品目列表（只读）
- **AND** 持有 `manage_categories` 授权或 admin 用户 MUST 能看到并使用这些写入口

### Requirement: 数据范围必须由管理授权决定（admin 除外）

`DataScopeMixin` 的数据范围 MUST 由员工被授予的组织节点授权计算得出，MUST NOT 由 `role` 职位推导；授权范围 MUST 通过显式声明的字段映射应用，而非探测模型字段名。

#### Scenario: 数据范围按授权计算

- **WHEN** 非 admin 员工查询资产列表
- **THEN** 返回结果 MUST 仅包含其被授权组织节点范围内的资产
- **AND** MUST NOT 返回其授权范围之外的资产

#### Scenario: 无授权非 admin 用户的数据范围

- **WHEN** 一个无任何组织节点授权的非 admin 员工查询业务数据
- **THEN** 系统 MUST 返回空范围（或仅自身相关数据，按声明的模型约定）
- **AND** MUST NOT 因缺失授权而放行全部数据

#### Scenario: 数据范围异常不静默降级

- **WHEN** 计算数据范围过程中发生异常
- **THEN** 系统 MUST 显式上报错误
- **AND** MUST NOT 静默降级为返回全部数据（避免越权）

### Requirement: 超级管理员 admin 必须拥有全部权限且不参与授权

`role == 'admin'` 的超级管理员 MUST 拥有全部数据范围与全部业务操作权限，且其权限 MUST NOT 依赖于授权表记录。

#### Scenario: admin 全权且不走授权

- **WHEN** admin 用户查询任意业务数据或调用任意操作
- **THEN** 系统 MUST 放行并返回全部数据
- **AND** 系统 MUST NOT 查询其授权表记录来决定权限

#### Scenario: 误删授权不影响 admin

- **WHEN** admin 的所有授权记录被删除
- **THEN** admin 仍 MUST 保持全部权限
- **AND** 系统 MUST 保持可用（不锁死）

### Requirement: 必须提供从旧权限模型的数据迁移

系统 MUST 提供数据迁移，按现有 `role + region/branch` 推导的有效范围为现有员工种子授权，保证迁移后既有管理能力不丢失。

#### Scenario: supervisor 迁移保留大区管理权

- **WHEN** 数据迁移对一位持有 region 的 supervisor 执行
- **THEN** 系统 MUST 为其种子该大区的组织节点授权
- **AND** 迁移后其数据范围 MUST 与迁移前一致

#### Scenario: leader 与 staff 迁移保留分公司管理权

- **WHEN** 数据迁移对持有 branch 的 leader 或 staff 执行
- **THEN** 系统 MUST 为其种子该分公司的组织节点授权
- **AND** 迁移后其数据范围 MUST 与迁移前一致（不擅自收窄）

#### Scenario: admin 不参与迁移种子

- **WHEN** 数据迁移执行
- **THEN** 对 admin 用户 MUST NOT 种子任何授权记录
- **AND** admin 权限 MUST 完全由职位兜底决定

