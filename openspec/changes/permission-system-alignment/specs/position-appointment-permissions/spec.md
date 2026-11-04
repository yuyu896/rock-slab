## MODIFIED Requirements

### Requirement: 岗位模板（仅预填，不参与运行时鉴权）

系统 SHALL 提供版本化岗位默认权限基线并在新建员工或改岗时将基线权限写入账号级授权记录。岗位模板 MUST NOT 在请求运行时直接授予权限；运行时授权 MUST 只依据账号级授权记录和系统管理员内置身份。权限分配页 MUST 将员工当前实际生效权限显示为已勾选项，且 MUST NOT 显示“岗位默认”“个人追加”或“个人取消”等来源标签。

普通岗位的基线权限 MUST 作为版本化配置纳入代码版本控制，不得在运行时依赖工作区外的 Excel。已确认的默认集合为：行政组长包含 `view_dashboard`、`view_notifications`、`view_approval_reports`、`view_reports`、`view_categories`、`view_departments`、`view_suppliers`、`view_users`、`view_organizations`、`view_asset_ledger`、`view_instances`、`edit_instances`、`change_instance_assignee`、`print_instance_label`、`view_purchase`、`edit_purchase`、`delete_purchase_draft`、`approve_purchase`、`view_assignment`、`edit_assignment`、`delete_assignment_draft`、`approve_assignment`、`view_transfer`、`edit_transfer`、`delete_transfer_draft`、`approve_internal_transfer`、`view_recovery`、`view_recovery_ledger`、`edit_recovery`、`delete_recovery_draft`、`approve_recovery`、`view_inventory`、`edit_inventory`、`review_inventory`。大区负责人基线为行政组长基线加 `edit_users`、`edit_organizations`、`delete_organizations`。分公司行政基线为行政组长基线移除 `approve_recovery` 和 `review_inventory`。三个普通岗位均不得默认获得 `view_reconciliation`，且 `view_audit_logs` 仅系统管理员可用，不得授予普通岗位。系统管理员继续通过内置全权获得全部能力，不写入普通岗位基线。

新员工创建时 MUST 按其岗位写入默认权限；改岗时 MUST 清除旧岗位基线和个人调整，并按新岗位基线重置。其他既有账号级授权与数据范围行为见本变更新增要求。岗位 MUST NOT 扩大员工数据范围。

#### Scenario: 分配页按岗位显示当前实际授权
- **WHEN** 管理员打开员工权限配置或为新员工选择岗位
- **THEN** 权限勾选 MUST 反映该员工按岗位基线及个人调整解析后的实际权限
- **AND** 页面 MUST NOT 显示权限来源标签

#### Scenario: 新建员工获得岗位基线
- **WHEN** 管理员新建一名行政组长账号
- **THEN** 账号级授权 MUST 包含上述全部行政组长基线权限
- **AND** MUST NOT 包含 `view_reconciliation` 或 `view_audit_logs`

#### Scenario: 大区负责人基线包含组织管理权限
- **WHEN** 管理员新建一名大区负责人账号
- **THEN** 其权限 MUST 等于行政组长基线加 `edit_users`、`edit_organizations`、`delete_organizations`

#### Scenario: 分公司行政默认不开通回收和盘点审批
- **WHEN** 管理员新建一名分公司行政账号
- **THEN** 其权限 MUST 等于行政组长基线移除 `approve_recovery` 和 `review_inventory`
- **AND** MUST 保留采购、领用和调拨审批基线

#### Scenario: 岗位授权不参与运行时隐式鉴权
- **WHEN** 用户的岗位名称在请求期间发生变化，但账号级授权记录尚未按新岗位重置
- **THEN** 运行时 MUST 只按现存账号级授权记录判权
- **AND** MUST NOT 仅凭岗位名称直接赋予权限

#### Scenario: 系统管理员使用内置全权
- **WHEN** 系统管理员查看本人权限
- **THEN** 系统 MUST 通过内置全权提供能力
- **AND** MUST NOT 通过普通岗位基线或可编辑账号授权记录授予管理员权限

## ADDED Requirements

### Requirement: 现有员工补授与岗位基线变更必须保留个人决定

首次基线同步 MUST 只处理在职员工，将岗位基线与该员工已有明确授权合并，不得删除既有授权或改变其数据范围。无法确认映射的旧权限码 MUST 保留为待核对记录且 MUST NOT 自动转换为新权限。后续修改岗位基线 MUST 先生成逐员工权限差异供管理员审阅，经确认后才生效，并 MUST 保留个人追加与个人取消。

账号实际权限 MUST 按“岗位基线 + 个人追加 - 个人取消”解析。权限分配页展示解析后的实际权限，不显示来源标签。停用账号保留实际授权和数据范围；重新启用时同步当前岗位基线，同时保留个人追加、个人取消和当前数据范围。

#### Scenario: 首次同步只补授基线
- **WHEN** 管理员首次同步现有在职员工的岗位基线
- **THEN** 每名员工获得其岗位默认权限
- **AND** 既有明确授权与新基线取并集
- **AND** 原数据范围保持不变
- **AND** 无法无损映射的旧权限被列为待核对且不转换

#### Scenario: 岗位基线变更先经确认
- **WHEN** 管理员修改某岗位默认权限
- **THEN** 系统 MUST 先显示受影响员工及其权限增减
- **AND** 确认前 MUST NOT 更新岗位基线或员工有效权限

#### Scenario: 个人追加和取消跨基线更新保留
- **WHEN** 管理员确认岗位基线更新
- **THEN** 员工个人追加权限 MUST 保留
- **AND** 对基线权限的个人取消 MUST 继续保持取消

#### Scenario: 停用和重新启用保留授权与范围
- **WHEN** 员工账号被停用后重新启用，且期间岗位和分公司未改变
- **THEN** 账号 MUST 按当前岗位同步基线并保留个人追加、个人取消及当前数据范围
