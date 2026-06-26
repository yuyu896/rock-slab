# 管理权限授权模型（management-permissions delta）

组织节点授权新增"整个组织架构（全部数据）"类型。

## MODIFIED Requirements

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
