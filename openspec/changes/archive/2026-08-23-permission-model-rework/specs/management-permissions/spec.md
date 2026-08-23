## MODIFIED Requirements

### Requirement: 数据范围必须由管理授权决定（admin 除外）

`DataScopeMixin` 的数据范围 MUST 由员工被授予的组织节点授权 **与其担任的树负责人任命**（区域 manager / 行政组 leader / 分公司 manager）的并集计算得出，MUST NOT 由 `role` 岗位推导；授权范围 MUST 通过显式声明的字段映射应用，而非探测模型字段名。任命展开规则与节点授权一致：沿组织树展开为分公司集合（区域→行政组→分公司、行政组→分公司）。

#### Scenario: 数据范围按授权与任命计算

- **WHEN** 非 admin 员工查询资产列表
- **THEN** 返回结果 MUST 仅包含其授权组织节点与担任负责人的节点子树范围内的资产
- **AND** MUST NOT 返回其范围之外的资产

#### Scenario: 无授权且无任命的非 admin 用户的数据范围

- **WHEN** 一个无任何组织节点授权、亦未担任任何树负责人的非 admin 员工查询业务数据
- **THEN** 系统 MUST 返回空范围（或仅自身相关数据，按声明的模型约定）
- **AND** MUST NOT 因缺失授权而放行全部数据

#### Scenario: 数据范围异常不静默降级

- **WHEN** 计算数据范围过程中发生异常
- **THEN** 系统 MUST 显式上报错误
- **AND** MUST NOT 静默降级为返回全部数据（避免越权）
