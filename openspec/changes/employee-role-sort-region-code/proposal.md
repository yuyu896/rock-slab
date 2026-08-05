## Why

组织架构页两个展示问题：

1. 员工列表无序，高职级账号没有优先显示。**无区域归属的高级别账号**（行政总监 / 行政经理 / 管理员）应在点「启航集团」顶层时显示在列表**最上层**——通过按职级排序实现，不改动树结构。
2. 区域编码（`code`）在组织树隐藏，需要显示，便于识别区域。

## What Changes

- **员工列表按职级排序**（admin > director > manager > supervisor > leader > staff，复用 `ROLE_LEVELS`），高职级在前，同职级按姓名。点「启航集团」时，无区域的总监 / 经理 / 管理员自然排到最上层。
- **组织树区域节点显示编码**（名称 + code）。

## Capabilities

### New Capabilities

（无。）

### Modified Capabilities

- `unified-organization-page`: 员工列表职级排序；区域节点显示编码。

## Impact

- **前端**：`frontend/src/utils/orgTree.ts`（新增 `sortEmployeesByRole` 纯函数）、`frontend/src/views/Organization.vue`（`employees` 调排序、区域节点 label）。复用 `constants` 的 `ROLE_LEVELS`。
- **后端**：无改动。
- **数据**：无迁移。
- **部署**：仅前端，`deploy.sh`（前端 build + nginx reload）。
