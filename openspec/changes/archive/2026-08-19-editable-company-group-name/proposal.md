## Why

顶层「启航集团」当前是前端**硬编码**的虚拟根名（`Organization.vue` 里写死的 `label: '启航集团'`），无法在系统内修改。组织更名（或将来改名）需要管理员能在系统里编辑集团名，全局对所有用户生效。

## What Changes

- **新建 `Company` 单例模型**（后端，预置「启航集团」），存集团名。
- **API**：读集团名（所有登录用户）+ 改名（受 `manage_organizations`）。
- **前端**：组织树根节点显示 `Company.name`（替代硬编码）；选中集团根时顶部栏提供「编辑集团」操作（改名弹窗）。

## Capabilities

### New Capabilities

（无。）

### Modified Capabilities

- `unified-organization-page`: 顶层集团根从「前端虚拟节点」升级为「`Company` 单例模型」，name 可编辑、全局生效。

## Impact

- **后端**：`organizations/models.py`（`Company` 模型）、迁移 + seed（`get_or_create`「启航集团」）、serializer + view（GET/PATCH company）、URL。
- **前端**：`api/company.ts`（新增）、`Organization.vue`（加载 company、根 label 用 `company.name`、编辑集团弹窗）。
- **数据**：新建 `Company` 表，seed 一条「启航集团」。
- **部署**：`deploy.sh`（后端 migrate + seed + 前端 build）。
