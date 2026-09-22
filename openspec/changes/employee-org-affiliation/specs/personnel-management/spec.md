## ADDED Requirements

### Requirement: 员工组织归属三态（分公司/行政组/大区至多一个，可全空）

员工组织归属 SHALL 支持三种节点之一：分公司（现状）、行政组（无分公司）、大区（无分公司无组），且 MUST 至多归属一个节点；无归属（三者皆空）MUST 允许。挂分公司的员工其行政组/大区归属 MUST 沿组织树派生（branch→team→region）而非单独存储；挂行政组的员工 region 沿 team 派生。用户序列化 MUST 输出按实际归属派生的 `team_name` / `region_name` / `branch_name`。员工归属 MUST NOT 产生数据范围——数据范围仍由任命（区/组/司负责人）与管理授权决定。

#### Scenario: 挂行政组（无分公司）
- **WHEN** 管理员将员工杨茜茜的组织归属设为「杨茜茜组」（不设分公司）
- **THEN** 系统 MUST 存储其 team 归属、branch 为空
- **AND** 其列表展示 MUST 显示 region_name=杨茜茜组所属大区、team_name=杨茜茜组、branch_name 为空

#### Scenario: 挂大区（无组无分公司）
- **WHEN** 管理员将员工归属设为「李海霞区」（不设组与分公司）
- **THEN** 系统 MUST 存储其 region 归属，team/branch 均为空

#### Scenario: 至多一个归属（互斥校验）
- **WHEN** 请求同时携带 branch 与 team（或 region）归属
- **THEN** API MUST 拒绝（400）并提示只能归属一个组织节点；数据库层 MUST 以约束兜底

#### Scenario: 无归属允许
- **WHEN** 员工三个归属字段均为空
- **THEN** 保存 MUST 成功，展示时区/组/分公司列为空

#### Scenario: 归属不产生数据范围
- **WHEN** 员工仅被归属到某大区（未被任命、未获授权）
- **THEN** 其数据范围 MUST 为空（resolve_user_scope 不读取归属字段）

### Requirement: 移动员工逐层可确认

组织架构页「移动员工」弹窗 SHALL 保持 区域 → 行政组 → 分公司 三级级联，且每层 MUST 可直接确认：仅选区域即归属该大区；选到行政组确认即归属该组；选到分公司即归属该分公司（现状行为）。选深层时 MUST 自动清空浅层归属以维持互斥。

#### Scenario: 移动到行政组（不选分公司）
- **WHEN** 管理员为无分公司的员工选择区域「李梦婷区」与行政组「杨茜茜组」后直接确认
- **THEN** 员工归属更新为该行政组（branch 清空），提示成功

#### Scenario: 移动到分公司（现状保持）
- **WHEN** 管理员级联选到具体分公司并确认
- **THEN** 员工归属更新为该分公司，region/team 存储为空（沿树派生）

## MODIFIED Requirements

### Requirement: Create personnel account
The system SHALL provide a "新增人员" button in the personnel management tab. Clicking it SHALL open a modal form with required fields: name, phone, role, and optional fields: 组织归属（大区/行政组/分公司三选一，可全空）、initial password. The default initial password SHALL be "123456". 组织归属字段 MUST 互斥（至多一个节点）。

#### Scenario: Create new personnel successfully
- **WHEN** user fills in name "张三", phone "13800138000", role "manager", selects 归属行政组「杨茜茜组」(不选分公司), and clicks "确定保存"
- **THEN** the system SHALL send `POST /api/users/` with the form data (team 归属、branch 为空) and password, show success message "创建成功", and refresh the list

#### Scenario: Create with missing required fields
- **WHEN** user submits the form without filling required fields
- **THEN** the system SHALL NOT submit and SHALL highlight the missing required fields

### Requirement: Edit personnel
The system SHALL provide an edit button in each row's action column. Clicking it SHALL open a modal pre-filled with the personnel's current data. 组织归属编辑 SHALL 与移动弹窗同口径（三选一级联、可清空）。

#### Scenario: Edit personnel successfully
- **WHEN** user changes the name from "张三" to "李四" and clicks "确定保存"
- **THEN** the system SHALL send `PUT /api/users/<id>` with updated data, show success message "保存成功", and refresh the list

#### Scenario: Edit affiliation to region-only
- **WHEN** user 将员工归属从「32分宁波」改为仅选大区「林丹妮区」并保存
- **THEN** the system SHALL send branch=null、team=null、region=该大区，保存成功且列表区列更新
