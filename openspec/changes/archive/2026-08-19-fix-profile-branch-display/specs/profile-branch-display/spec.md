## ADDED Requirements

### Requirement: 用户接口返回分公司与区域名称
`UserSerializer` SHALL 额外返回只读的分公司名称（`branch_name`）与区域名称（`region_name`），同时保留 `branch`/`region` 外键 id 用于创建/更新写入。

#### Scenario: 有分公司返回名称
- **WHEN** 用户已归属某分公司
- **THEN** 接口返回的 `branchName` 为该分公司名称（而非 UUID）

#### Scenario: 未归属分公司
- **WHEN** 用户未设置分公司
- **THEN** `branchName` 为 null

#### Scenario: 创建/更新仍用外键 id
- **WHEN** 创建或更新用户并指定分公司
- **THEN** 通过 `branch` 外键 id 写入，`branch_name` 为只读派生字段

### Requirement: 个人中心显示真实分公司名称
个人中心（`UserPanel`）的「所属分公司」SHALL 显示分公司名称，而非外键 UUID。

#### Scenario: 显示分公司名称
- **WHEN** 已登录用户打开个人中心且已归属分公司
- **THEN** 「所属分公司」显示该公司名称（头部分司标签与信息区一致）

#### Scenario: 未设置分公司
- **WHEN** 用户未归属分公司
- **THEN** 「所属分公司」显示「未设置」（不显示 UUID 或乱码）
