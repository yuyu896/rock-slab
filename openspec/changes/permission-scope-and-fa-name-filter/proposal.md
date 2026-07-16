## Why

1. **权限分配后看不到内容**：管理员通过权限分配页给员工开通了分公司/区域的管理权限（OperationGrant），但该员工登录后仍查看不了对应数据。需排查根因：可能是分配操作授权时**未同步创建数据范围 (ManagementScope)**，导致有操作权限但 DataScopeMixin 返回空集。
2. **固定资产表缺资产名称筛选**：FixedAssetList 当前有分公司/状态/关键字筛选，但缺少一个独立的**资产名称**筛选栏。

## What Changes

### A. 权限数据范围修复
- 排查 PermissionAssign 页面分配操作授权时是否同步创建 ManagementScope。
- 确保开通分公司/区域管理权限后，该用户的数据范围**自动包含**对应分公司/区域，能看到对应数据。
- 若需手动分配数据范围，确保 UI 引导明确（分配操作授权时自动带出数据范围选择）。

### B. 固定资产表资产名称筛选
- FixedAssetList 加一个**资产名称**筛选栏（独立输入框或下拉）。
- 后端 FixedAssetFilterSet 加 `资产名称` 精确/模糊过滤。

## Capabilities

### New Capabilities
- `permission-scope-and-fa-name-filter`: 权限分配后数据范围同步 + 固定资产表资产名称筛选。
