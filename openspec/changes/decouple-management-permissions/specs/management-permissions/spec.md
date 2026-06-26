# 管理权限授权模型（management-permissions）

将"职位/组织归属"与"管理权限"解耦：新增独立授权模型，支持按组织节点（大区/分公司/行政组）与业务操作（模块/动作）两个维度为员工授予管理权限；admin 走职位最高权限，不参与授权。

## ADDED Requirements

### Requirement: 系统必须支持按组织节点授予管理权限

系统 MUST 提供组织节点维度的管理授权，可为任意非 admin 员工授予管理某些大区、分公司或行政组的权限；授权 MUST 可叠加（一个员工可持有多条授权，范围取并集）。

#### Scenario: 授予大区管理权

- **WHEN** 管理员为员工 A 授予"管理华东大区"的组织节点授权
- **THEN** 系统 MUST 存储 A 对该大区的管理授权
- **AND** A 的数据范围 MUST 包含该大区旗下全部分公司与行政组

#### Scenario: 授予单一行政组管理权

- **WHEN** 管理员为一位行政主管授予"仅管理行政组 X"的授权（该主管职位仍为 supervisor）
- **THEN** 该主管的数据范围 MUST 仅收窄至行政组 X
- **AND** MUST NOT 因其职位为 supervisor 而扩展到整个大区

#### Scenario: 跨组织授权叠加

- **WHEN** 员工 B 同时被授予分公司 F1 与行政组 T2 的管理权
- **THEN** B 的数据范围 MUST 为 F1 全部数据与 T2 数据的并集

### Requirement: 系统必须支持按业务操作授予管理权限

系统 MUST 提供业务操作维度的授权，可为员工授予具体的业务操作权限（如审批采购、管理用户）；接口级权限 MUST 基于员工是否持有对应操作授权来判断，而非职位等级。

#### Scenario: 持有操作授权方可执行

- **WHEN** 员工 C 被授予 `approve_transfer` 操作授权
- **THEN** C 调用资产调拨审批接口时 MUST 被放行
- **AND** 未被授予该操作的员工 D（非 admin）调用同一接口 MUST 被拒绝（403）

#### Scenario: 接口权限不再依赖职位等级

- **WHEN** 一位 `staff` 职位的员工被授予某业务操作授权
- **THEN** 该员工执行该操作时 MUST 被放行
- **AND** 系统 MUST NOT 因其职位等级为 staff 而拒绝

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
