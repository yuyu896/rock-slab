## MODIFIED Requirements

### Requirement: 岗位模板（仅预填，不参与运行时鉴权）
系统 SHALL 提供岗位模板注册表（四岗），岗位 = 权限预填模板：`admin`→系统管理员（运行时恒真，无需授予）、`director`→大区负责人（预填区域类全量操作码）、`manager`→**分公司行政**（scope_type=branch，预填 6 操作码：manage_assets / view_audit / view_all_notifications / view_reports / manage_instances / dispose_assets）、`leader`→行政组长（模板为空，价值在任命范围）。岗位模板 MUST 仅用于分配时预填操作码勾选；运行时鉴权 MUST 只依据 OperationGrant 授权表与 admin 身份，MUST NOT 读取岗位。

#### Scenario: 分配页按岗位预填操作码
- **WHEN** 管理员在分配页为员工选择岗位「分公司行政」
- **THEN** 操作码勾选区按该岗位模板预填 6 项（manage_assets / view_audit / view_all_notifications / view_reports / manage_instances / dispose_assets），且可增删后保存

#### Scenario: 岗位不产生隐式运行时权限
- **WHEN** 某员工岗位为「大区负责人」但未被授予任何操作码且未被任命
- **THEN** 其 `can(任意操作码)` 为假（admin 除外），数据范围为空

#### Scenario: 门禁按模板校验 manager 抽样
- **WHEN** `check_seed_grants` 抽取一位 manager 账号核对操作授权
- **THEN** 其授权集合 MUST 覆盖 6 项目标集合（manage_assets / view_audit / view_all_notifications / view_reports / manage_instances / dispose_assets）
