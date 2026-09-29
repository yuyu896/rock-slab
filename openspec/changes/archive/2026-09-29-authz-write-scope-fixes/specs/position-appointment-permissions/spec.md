# position-appointment-permissions Delta

## MODIFIED Requirements

### Requirement: 任命即授权（树负责人 = 子树范围）
员工被任命为组织树负责人（`Region.manager` / `Team.leader` / `Branch.manager`）时，其数据范围 MUST 自动包含该节点的整个子树，与组织节点授权（ManagementScope）范围取并集；任命 MUST 实时生效（编辑负责人字段后立即反映，无需任何授权记录）。一人兼任多个负责人职位时范围 MUST 取并集。**任命字段的写入与变更 MUST 仅限 admin**：非 admin 请求中任命字段发生值变更（含新建携带非空任命）MUST 返回 400 拒绝；`manage_organizations` 操作码授予组织节点的编辑能力，MUST NOT 隐含任命/免任权。

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

#### Scenario: 非 admin 变更任命被拒
- **WHEN** 持 `manage_organizations` 的非 admin 用户 PATCH 组织节点将任命字段改为他人（或新建节点携带非空任命）
- **THEN** 系统返回 400（任命/免任仅系统管理员可操作），任命不变更

#### Scenario: 非 admin 值未变的节点编辑放行
- **WHEN** 持 `manage_organizations` 的非 admin 用户 PATCH 组织节点仅改名称/编码等，请求中任命字段与现值一致（或不携带）
- **THEN** 编辑正常生效，不因任命字段被拒

#### Scenario: admin 任命路径不受影响
- **WHEN** admin 通过权限分配页（组织 API）任命/改任/免任树负责人
- **THEN** 任命正常写入并实时生效
