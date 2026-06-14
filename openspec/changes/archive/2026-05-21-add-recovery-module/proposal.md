## Why

资产流转模块目前仅覆盖采购入库、领用出库、调拨三种操作，缺少资产回收管理能力。行政资产在使用周期结束后需要统一的回收登记和跟踪，以形成完整的资产全生命周期管理闭环。

## What Changes

- 在资产流转侧边栏下新增"回收"板块入口
- 新增前端页面 `RecoveryList.vue`，展示回收记录列表，表头包含：序号、分公司、资产编号、资产类目、物品分类、资产名称、回收分类、入库日期、数量、单位、规格、出库日期、所属部门、当前处理状态、存放位置、经办人、备注
- 新增前端路由 `/transfers/recovery`
- 后端新增 `recovery` 操作类型（Transfer 模型的 action_type 新增选项）
- 后端 API 支持按 `recovery` 类型筛选流转记录
- 回收记录支持新建、查看详情、导出功能

## Capabilities

### New Capabilities

- `recovery-list`: 回收记录列表页面，包含筛选、分页、新建、详情查看、导出功能

### Modified Capabilities

（无现有规格变更，新增操作类型属于模型层扩展，不影响已有流转功能的行为规格）

## Impact

- **后端**: `backend/apps/transfers/models.py` — Transfer 模型 ACTION_CHOICES 新增 `recovery`；`views.py` 支持新类型；序列化器和过滤器适配
- **前端**: `frontend/src/views/transfers/RecoveryList.vue` — 新增页面；`frontend/src/composables/useTransferList.ts` — 新增 recovery 类型元数据；`SidebarNav.vue` — 新增菜单项；`router/index.ts` — 新增路由
- **API**: `frontend/src/api/transfers.ts` — 新增 `recoverAsset` 函数
