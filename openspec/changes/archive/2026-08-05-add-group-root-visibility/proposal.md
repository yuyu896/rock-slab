## Why

组织架构页缺少顶层架构，且存在员工可见性盲区：**全无归属的员工**（`branch`/`team`/`region` 都空）在任何组织节点都看不到，只能靠搜索——被误认为"账号缺失"（如 180男神）。需要一个顶层「启航集团」一览全组织，并确保所有员工至少在顶层可见，不被隐藏。

管理层级（行政总监 / 行政经理 → 区域）**不在本提案范围**，后续单独提案。

## What Changes

- **加顶层虚拟根「启航集团」**（前端虚拟节点，无后端模型），所有区域挂其下。
- **集团根选中时显示所有员工**（含全无归属），不再隐藏任何人。
- **确保各层级员工不隐藏**：区域节点显示区长等无下级归属的员工。

## Capabilities

### New Capabilities

（无。）

### Modified Capabilities

- `unified-organization-page`: 新增「顶层集团根（启航集团）」「各层级员工不隐藏」两项要求。

## Impact

- **前端**：`frontend/src/views/Organization.vue`（树渲染集团根层 + 顶部栏）、`frontend/src/utils/orgTree.ts`（`NodeType` 加 `group`、`filterEmployeesByNode` 加 group 分支返回全员）。
- **后端**：无改动（集团为前端虚拟根，无新模型）。
- **数据**：无迁移。
- **部署**：仅前端，`deploy.sh`（前端 build + nginx reload）。
