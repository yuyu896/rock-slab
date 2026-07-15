## ADDED Requirements

### Requirement: 组织架构管理界面所有人可查看
组织架构的区域/分公司/行政组/人员管理界面 SHALL 对所有登录用户可见，包括标签入口与数据展示，且不得因角色将用户强制切离。

#### Scenario: 普通员工可见管理标签
- **WHEN** 普通员工（非 supervisor）进入组织架构模块
- **THEN** 能看到并切换到 区域/分公司/行政组/人员 管理标签，并查看其数据

#### Scenario: 不被强制切回架构图
- **WHEN** 普通员工停留在某管理标签
- **THEN** 不会被自动切回「组织架构图」标签

### Requirement: 修改按操作授权
管理界面的「新增/编辑/删除」操作 SHALL 仅对持相应授权的用户可见：区域/分公司/行政组需 `manage_organizations`；人员需 `manage_users`。

#### Scenario: 无组织授权看不到区域/分公司/行政组的修改入口
- **WHEN** 无 `manage_organizations` 授权的用户查看区域/分公司/行政组管理
- **THEN** 看不到「新增/编辑/删除」按钮

#### Scenario: 无 manage_users 看不到人员的修改入口
- **WHEN** 无 `manage_users` 授权的用户查看人员管理
- **THEN** 看不到人员的「新增/编辑/删除」按钮

#### Scenario: 有授权者可见可改
- **WHEN** 持有对应授权的用户查看管理界面
- **THEN** 可见并可使用「新增/编辑/删除」
