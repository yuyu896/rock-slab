## ADDED Requirements

### Requirement: 敏感写 action 必须声明权限码

审批、入库、导入、批量删除等敏感写 action MUST 在 ViewSet 的 `required_operations` 中显式声明所需操作码，未声明的此类写 action 不得放行。业务发起类 action（流转 `purchase/assign/return/transfer/recovery`、资产 `create`）按产品设计对所有登录用户开放（员工申请领用 / 采购 / 登记资产），不要求 `manage_assets`，其数据范围由「写操作必须校验目标分公司在授权范围」约束。

#### Scenario: 流转导入未授权被拒
- **WHEN** 一个无 `manage_assets` 授权的用户 `POST /api/transfers/import-excel`
- **THEN** 系统返回 403，不解析文件

#### Scenario: 业务发起对所有登录用户开放但受范围约束
- **WHEN** 一个已登录用户 `POST /api/transfers/transfer`（或 purchase / assign 等业务发起）或 `POST /api/assets/`
- **THEN** 接口不在权限层拒绝；若目标分公司超出其授权范围，由范围校验返回 400

### Requirement: 写操作必须校验目标分公司在授权范围

流转创建（`purchase/assign/return/transfer/recovery`）与盘点任务创建 MUST 校验其 `from_branch` / `to_branch` / `branch` 均在 `resolve_user_scope(request.user).branches` 内；admin 豁免。任一目标分公司越界时 MUST 返回 400 且不落库。

#### Scenario: manager 为授权范围外的分公司发起调拨被拒
- **WHEN** 管辖区域 A 的 manager 发起一笔 `from_branch` 属于区域 B 的调拨
- **THEN** 系统返回 400，不创建流转单，资产库存不变

#### Scenario: supervisor 为授权范围外的分公司建盘点任务被拒
- **WHEN** 区域 A 的 supervisor 为区域 B 的分公司创建盘点任务
- **THEN** 系统返回 400，不生成盘点项、不污染目标分公司盘点状态

### Requirement: 盘点 check 必须校验资产属于任务所属分公司

盘点 `check` 接口 MUST 限定提交的 `asset` 属于 `task.branch`；提交不属于该分公司的资产 MUST 返回 404，且不得创建盘点项。

#### Scenario: 提交跨范围资产进行盘点被拒
- **WHEN** 持 A 分公司盘点权限的用户对 A 分公司任务提交一个 B 分公司资产的 `asset_id`
- **THEN** 系统返回 404，不创建 InventoryItem，审批后该资产库存不受影响

### Requirement: 用户列表与详情必须遵循数据范围隔离

`UserViewSet` 的 list / retrieve MUST 返回 `_get_user_queryset(request.user)` 过滤后的结果（admin 全量；其余为授权组织节点内 + 本人）；不得向无权用户暴露范围外用户的 `phone`（登录账号）。

#### Scenario: 非 admin 用户只能看到范围内的用户
- **WHEN** 一个 manager 调用 `GET /api/users/`
- **THEN** 响应仅包含其授权范围内的用户与本人，不包含其他区域用户

#### Scenario: 无授权用户看不到全公司手机号
- **WHEN** 一个无 `manage_users` 授权的 staff 调用 `GET /api/users/`
- **THEN** 响应不包含其授权范围外任何用户的 `phone` 字段
