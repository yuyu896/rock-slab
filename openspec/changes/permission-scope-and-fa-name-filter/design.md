## Context

### 权限系统现状
- **OperationGrant**（操作授权）：决定"能不能做"（如 manage_organizations）。OperationPermission 检查。
- **ManagementScope**（数据范围）：决定"能看到哪些数据"。DataScopeMixin 的 `resolve_user_scope` 读取。
- 两者**独立**——开通 OperationGrant 不自动创建 ManagementScope。
- Organization ViewSets（Region/Branch/Team）**不继承 DataScopeMixin**，读操作对所有人放行——所以组织架构数据本身应该看得到。
- 资产/流转等模块**继承 DataScopeMixin**——数据范围未配置则返回空集。
- **推断**：员工看不到内容可能不是组织架构本身，而是**资产/流转等其他模块**的数据——因为开了操作权限但没配数据范围。

### 固定资产筛选现状
- FixedAssetList 有分公司/状态/关键字筛选。关键字搜多字段（含资产名称）。
- FixedAssetFilterSet 有 branch/asset_code/status/keyword。无独立资产名称过滤。

## Decisions

### 决策 1：排查 + 修复权限数据范围
- 排查 PermissionAssign 页面是否在分配操作授权时同步创建 ManagementScope。
- 若未同步：在 PermissionAssign 保存操作授权时，自动创建/更新对应 ManagementScope（按选定的分公司/区域）。
- 若已同步但 scope 解析有 bug：修复 `resolve_user_scope`。

### 决策 2：固定资产表加资产名称筛选栏
- 前端 FixedAssetList 加「资产名称」筛选输入框。
- 后端 FixedAssetFilterSet 加 `资产名称 = CharFilter(field_name='资产名称')`。

## Risks
- 权限问题根因需进一步排查（可能是前端/后端/数据多种原因），本提案先排查再定方案。
- 自动创建 ManagementScope 需注意权限边界（不能越权扩大范围）。

## Open Questions
1. 员工看不到的具体是哪个模块的数据？（组织架构 / 资产 / 流转？）—— 需用户确认。
