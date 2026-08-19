## Context

- `UserSerializer`（`apps/users/serializers.py`）的 `Meta.fields` 含 `branch`、`region` 等外键，未显式声明字段 → DRF 以 `PrimaryKeyRelatedField` 序列化为 **UUID 主键**。
- 个人中心 `UserPanel` 接收 `userInfo` prop（来自 `userStore.profile`，即 `UserSerializer` 输出），把 `userInfo.branch`（UUID）当文本渲染（头部标签 + 信息区「所属分公司」）。
- 项目用 `djangorestframework-camel-case`：后端 `branch_name` → 前端 `branchName`。
- `User` 的 `branch`/`region` 为外键；`Branch.name`、`Region.name` 为名称字段。

## Goals / Non-Goals

**Goals:**
- 个人中心「所属分公司」显示真实分公司名称。
- 不破坏用户创建/更新时按 `branch` 外键 id 写入。

**Non-Goals:**
- 不改其他消费方（如用户管理列表 `PersonnelManager`）的同类显示——`branchName` 已可用，按需复用。
- 不处理 `leader`/`team` 的同类潜在 UUID 显示（本变更只修分公司，`region` 顺带）。

## Decisions

### 决策 1：后端用 SerializerMethodField 加 branch_name/region_name（只读）
- **做法**：`UserSerializer` 新增 `branch_name = SerializerMethodField()`（返回 `obj.branch.name if obj.branch else None`）、`region_name` 同理；加入 `Meta.fields`。保留 `branch`/`region` 原外键字段供写入。
- **理由**：新增只读名称字段是增量、不破坏写入；驼峰自动转 `branchName`。
- **备选**：把 `branch` 改为 `StringRelatedField` 返回名称——会破坏创建/更新的外键写入，**否**。

### 决策 2：前端显示 branchName
- **做法**：`UserPanel` 两处 `userInfo.branch` → `userInfo.branchName`（`UserInfo` 类型加 `branchName?: string`）。
- **理由**：直接消费后端返回的名称。

## Risks / Trade-offs

- **[类型缺失]** `UserInfo` 类型无 `branchName` → **缓解**：加可选字段 `branchName?: string`。
- **[其他页面同类问题]** 用户管理列表若也显示 `branch` UUID，同样会乱码 → **缓解**：`branchName` 已由接口提供，其他页面可按需改用；本变更只修个人中心（见 Non-Goals）。
- **[历史数据]** 部分用户无 `branch` → **缓解**：`branch_name` 返回 `None`，前端回退显示「未设置」。

## Migration Plan

1. 后端：`UserSerializer` 加两个只读名称字段。
2. 前端：`UserPanel` 改显示 + 类型补字段。
3. 纯前后端逻辑，**无 DB 迁移**；部署即生效。

## Open Questions

1. 是否一并修用户管理列表（`PersonnelManager`）等页面的同类 UUID 显示？默认**只修个人中心**（`branchName` 已可用，其余按需）。

> **范围核查结论（已确认）**：全仓排查后，**仅 `UserPanel`（个人中心）直接渲染 `userInfo.branch`（UUID）**。
> - `PersonnelManager`（用户管理列表）、`TeamManager`、`OrganizationBranch` 已用客户端查表 helper（`getBranchName`/`getRegionName`/`getUserName`/`getTeamName`）把 UUID 转名称——**正常，无需改**。
> - `Dashboard`（活动显示 `调出分公司→调入分公司` 名称）、`Purchase`/`PurchaseDetail`（订单显示分公司名称）——均显示名称，**正常**。
> - `MobileScan` 的 `taskInfo.branch` 取的是 `branchId`（盘点任务外键 id），属**盘点模块另一数据源**，非用户档案；本变更不纳入，作为单独事项另行处理。
> 故本变更实际只修 `UserPanel`（+ 后端 `branch_name`/`region_name` 供其消费）。
