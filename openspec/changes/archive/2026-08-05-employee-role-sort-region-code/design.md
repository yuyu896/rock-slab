## Context

当前 `employees` 列表无排序（按 `users` 数组顺序）。组织树区域节点只显示 `name`。前端 `constants/index.ts` 已有 `ROLE_LEVELS`（admin=1 … staff=6），与后端 `core/permissions.py` 一致。集团根（启航集团）已显示全员（含无区域归属）。

## Goals / Non-Goals

**Goals:**
- 员工按职级排序（高职级在前）。
- 区域节点显示编码。

**Non-Goals:**
- 不改树结构（管理层级不进树，靠排序 + 顶层全员显示体现）。
- 不改后端。

## Decisions

### D1. 抽 `sortEmployeesByRole` 纯函数，复用 `ROLE_LEVELS`
**选择**：`orgTree.ts` 新增 `sortEmployeesByRole(users)`：按 `ROLE_LEVELS[role]` 升序（admin=1 在前），同职级按 `name` 升序。`employees` computed 在 `filterEmployeesByNode` 后调用它。
**理由**：复用现有 `ROLE_LEVELS`（前后端一致）；抽纯函数便于单元测试（与既有 `filterEmployeesByNode` 模式一致）。点集团根时，无区域的总监 / 经理 / 管理员（职级高）排到最上层，体现管理层级——无需树结构改动，与「员工不进树」一致。

### D2. 区域节点显示编码
**选择**：组织树区域节点 label 显示「名称（编码）」，如「华东区域（HD）」。
**理由**：编码识别区域，便于管理。

## Risks / Trade-offs

- **[排序性能]** 小规模（当前 21 人）无碍；大规模仍可接受（纯内存排序）。

## Migration Plan

仅前端改动。部署：`deploy.sh`（前端 build + nginx reload），无后端 migrate。

## Open Questions

（无。）
