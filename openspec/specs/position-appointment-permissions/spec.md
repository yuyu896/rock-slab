# position-appointment-permissions Specification

## Purpose
TBD - created by archiving change permission-model-rework. Update Purpose after archive.
## Requirements
### Requirement: 岗位模板（仅预填，不参与运行时鉴权）
系统 SHALL 提供岗位模板注册表（四岗），岗位 = 权限预填模板：`admin`→系统管理员（运行时恒真，无需授予）、`director`→大区负责人（预填区域类全量操作码）、`manager`→**分公司行政**（scope_type=branch，预填 8 操作码：manage_users / manage_dictionary / manage_assets / approve_transfer / approve_inventory / adjust_ledger / manage_instances / view_reports）、`leader`→行政组长（模板为空，价值在任命范围）。岗位模板 MUST 仅用于分配时预填操作码勾选；运行时鉴权 MUST 只依据 OperationGrant 授权表与 admin 身份，MUST NOT 读取岗位。

#### Scenario: 分配页按岗位预填操作码
- **WHEN** 管理员在分配页为员工选择岗位「分公司行政」
- **THEN** 操作码勾选区按该岗位模板预填 8 项（manage_users / manage_dictionary / manage_assets / approve_transfer / approve_inventory / adjust_ledger / manage_instances / view_reports），且可增删后保存

#### Scenario: 岗位不产生隐式运行时权限
- **WHEN** 某员工岗位为「大区负责人」但未被授予任何操作码且未被任命
- **THEN** 其 `can(任意操作码)` 为假（admin 除外），数据范围为空

### Requirement: 任命即授权（树负责人 = 子树范围）
员工被任命为组织树负责人（`Region.manager` / `Team.leader` / `Branch.manager`）时，其数据范围 MUST 自动包含该节点的整个子树，与组织节点授权（ManagementScope）范围取并集；任命 MUST 实时生效（编辑负责人字段后立即反映，无需任何授权记录）。一人兼任多个负责人职位时范围 MUST 取并集。

#### Scenario: 大区负责人获得全区范围
- **WHEN** 员工 X 被设为区域 R 的 manager（无任何 ManagementScope 授权）
- **THEN** X 的数据范围包含 R 旗下（经行政组）全部分公司

#### Scenario: 行政组长获得组内范围
- **WHEN** 员工 Y 被设为行政组 T 的 leader
- **THEN** Y 的数据范围包含 T 组内全部分公司

#### Scenario: 任命与授权并集
- **WHEN** 员工 Z 被任命为分公司 B1 负责人，同时持分公司 B2 的节点授权
- **THEN** Z 的数据范围包含 B1 与 B2

#### Scenario: 卸任即回收
- **WHEN** 区域负责人被改任为他人
- **THEN** 原负责人的数据范围即时不再包含该区域子树（除非另有授权）

### Requirement: 岗位目录接口
系统 SHALL 提供 `GET /api/permissions/position-templates` 返回岗位模板目录（岗位标识、名称、任命节点类型提示、预填操作码清单），供分配页消费。

#### Scenario: 获取岗位模板
- **WHEN** 管理员请求岗位模板目录
- **THEN** 返回 admin/director/manager/leader 四个岗位及各自预填操作码与节点类型提示，不含 supervisor 与 staff

### Requirement: staff 岗位退役
系统 MUST NOT 再提供 staff 作为可分配岗位：岗位模板、岗位目录、用户创建/编辑接口的岗位可选项 MUST NOT 含 staff；岗位分配权线（谁能分配哪些岗位）MUST NOT 含 staff。存量 staff 用户的读取与鉴权 MUST NOT 报错（按其既有授权正常工作），并 SHALL 由迁移工具换岗为 manager。

#### Scenario: 创建用户不可选 staff
- **WHEN** 以 role=staff 创建用户
- **THEN** 返回 400 校验错误

#### Scenario: 存量 staff 不炸
- **WHEN** 存量 role=staff 用户正常请求业务接口
- **THEN** 按其 OperationGrant/ManagementScope/任命计算权限，无异常

### Requirement: 权限分配页保存脏检查与只补不删
权限分配页「保存岗位」的可用条件 MUST 为：岗位变化**或**操作码勾选集与该用户既有授权码集存在差集。换岗选择岗位模板时，操作码勾选集 MUST 初始化为**模板操作码 ∪ 既有授权码集**（MUST NOT 整体替换清空既有授权）；既有授权中不属于新模板的项 MUST 默认保留并 SHALL 在页面提示保留数量，仅显式取消勾选后才在保存时删除。保存写入语义与 `migrate_positions` 命令"只补不删"原则统一。

#### Scenario: 仅调整操作码可保存
- **WHEN** 管理员选中用户后未改岗位，仅勾选一项其未持有的操作码
- **THEN** 「保存岗位」按钮可用，保存后该操作码授予成功

#### Scenario: 无变化时不可保存
- **WHEN** 岗位未变且勾选集与既有授权码集一致
- **THEN** 「保存岗位」按钮禁用

#### Scenario: 换岗保留模板外既有授权
- **WHEN** 某用户持有模板外单独授予的 `dispose_assets`，管理员将其换岗为「分公司行政」并直接保存
- **THEN** 勾选集为模板 8 项 ∪ 既有授权（含 dispose_assets），保存后 dispose_assets 授权保留，页面曾提示"将保留岗位外的既有授权"

#### Scenario: 显式取消勾选才删除
- **WHEN** 管理员在勾选区显式取消某既有授权项后保存
- **THEN** 该授权被删除

### Requirement: supervisor 岗位退役
系统 MUST NOT 再提供 supervisor 作为可分配岗位：岗位目录、用户创建/编辑接口的岗位可选项 MUST NOT 含 supervisor；岗位分配权线（谁能分配哪些岗位）MUST NOT 含 supervisor。存量 supervisor 用户的读取与鉴权 MUST NOT 报错（按其既有授权正常工作），并 SHALL 由迁移工具换岗。

#### Scenario: 创建用户不可选 supervisor
- **WHEN** 以 role=supervisor 创建用户
- **THEN** 返回 400 校验错误

#### Scenario: 存量 supervisor 不炸
- **WHEN** 存量 role=supervisor 用户正常请求业务接口
- **THEN** 按其 OperationGrant/ManagementScope/任命计算权限，无异常

### Requirement: 操作码目录扩充
操作码目录 SHALL 在既有 9 项之上注册：`manage_dictionary`（管理品目字典）、`manage_instances`（管理固定资产实例）、`adjust_ledger`（台账调整单）、`dispose_assets`（资产处置），供分配授予；执行点由后续阶段接入。

#### Scenario: 新操作码可授予
- **WHEN** 管理员为员工授予 manage_dictionary
- **THEN** 授权记录创建成功并在操作目录与矩阵页可见

### Requirement: 通知路由按操作授权而非岗位
审批类通知的接收人 MUST 与运行时审批权限同口径：持有 `approve_transfer` 授权（或 admin）且数据范围覆盖相关分公司的活跃用户；审批通过抄送对象 MUST 为持有 `view_all_notifications` 的非 admin 用户且范围覆盖相关分公司。通知路由 MUST NOT 按角色列表筛人。

#### Scenario: 持审批授权者收到待审批通知
- **WHEN** 岗位为 staff 的用户被单独授予 approve_transfer 且范围含分公司 B，B 产生待审批单据
- **THEN** 该用户收到审批通知

#### Scenario: 无授权的高岗位不被路由
- **WHEN** 岗位为 director 的用户未被授予 approve_transfer 且非 admin，产生待审批单据
- **THEN** 该用户不收到审批通知

### Requirement: 岗位换岗迁移工具（逐人 diff，只补不删）
系统 SHALL 提供 `migrate_positions` 管理命令：默认 dry-run 输出逐人清单（岗位现值→目标岗位、按模板需补授的操作码、任命节点、生效范围）；`--apply` 执行换岗（存量退役岗位按映射换岗：supervisor→manager、staff→manager）并补建缺失操作码授权。执行 MUST NOT 删除任何既有授权（ManagementScope / OperationGrant）。

#### Scenario: dry-run 输出逐人清单
- **WHEN** 运行 `migrate_positions`（不带参数）
- **THEN** 输出每位非 admin 用户的岗位映射与补授清单，不写库

#### Scenario: apply 换岗 staff 并补授不删既有
- **WHEN** 运行 `migrate_positions --apply`，某存量 staff 用户已持有模板外的额外操作码
- **THEN** 其岗位更新为 manager，分公司行政模板 8 操作码补齐，ManagementScope 与既有额外授权保留

