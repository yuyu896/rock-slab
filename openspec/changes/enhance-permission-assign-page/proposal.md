## Why

权限分配页面（`decouple-management-permissions` 变更落地后）已能授予组织节点（大区/分公司/行政组）与业务操作，但存在三个体验与能力缺口：

1. **无法授予"全部数据"**：非 admin 用户若需跨全部大区管理（如旧 `manager` 角色"全部数据"的能力），只能逐个大区勾选；且后续新增的大区不会自动被覆盖，需反复补授权。缺少一个"整个组织架构"的授权类型。
2. **员工选择不可搜索**：当前是平铺下拉框，员工较多时难以定位，无法按姓名 / 手机号过滤。
3. **"授大区即含旗下分公司"不可见**：后端 `ScopeResolver` 已实现授大区→自动展开为旗下全部分公司，但 UI 既不在授予时提示、也不在已授权列表中体现，管理员无法确认授予某大区后实际覆盖了哪些分公司。

## What Changes

- **新增"整个组织架构（全部数据）"组织节点授权类型**：单条 `is_all_data` 授权即覆盖全部（含未来新增的）大区 / 分公司 / 行政组，等价于旧 `manager` 的"全部数据"能力，可用于非 admin 用户；与具体节点授权互斥，每用户至多一条。
- **员工选择器改为可搜索**：按姓名 / 手机号实时过滤，员工较多时可快速定位。
- **大区授权的覆盖范围可见**：授予大区时展示其旗下分公司列表；已授权列表中的大区项也展示覆盖分公司数，使"授大区即含全部分公司"对管理员透明。

## Capabilities

### New Capabilities
<!-- 无新增能力；本变更是对现有 management-permissions 能力的增量改进 -->

### Modified Capabilities
- `management-permissions`: 组织节点授权新增"整个组织架构（全部数据）"类型；该授权 MUST 覆盖全部组织节点（含未来新增节点），数据范围等价于 admin 的全部数据。

## Impact

- **后端模型**：`ManagementScope` 新增 `is_all_data` 布尔字段；调整 `CheckConstraint`（`is_all_data=True` 且三节点全空，或 `is_all_data=False` 且恰好一个节点）；新增条件唯一约束（每用户至多一条 `is_all_data` 授权）。
- **后端 scope**：`ScopeResolver` 命中 `is_all_data=True` → 返回全部数据（与 admin 同）。
- **后端序列化器**：`ManagementScopeSerializer` 暴露 `is_all_data`，并校验"全部数据"与具体节点互斥。
- **迁移**：纯结构迁移（新增字段 + 调整约束），无数据回填。
- **前端**：`views/admin/PermissionAssign.vue` 员工选择器改为可搜索；组织节点新增"全部数据"选项与展示；大区授权时展示旗下分公司列表。
- **测试**：覆盖 `is_all_data` 授权 → 全部数据范围；重复 `is_all_data` 拦截；`is_all_data` 与具体节点互斥校验。
