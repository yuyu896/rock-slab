## Context

- 资产列表（`AssetList.vue`）**已具备**行多选（复选框 + 全选 + `selectedAssets`）与批量操作栏（「批量打印标签 / 批量调拨」），并有单删（`handleDelete`，`deleteAsset`，`canManageAssets` 网关）。
- 固定资产表（`FixedAssetList.vue`）有单删（`handleDelete` / `deleteFixedAsset`，`canManageAssets` 网关），但**无多选、无批量栏**。
- 后端 `AssetViewSet` / `FixedAssetViewSet` 均为 `DataScopeMixin + ModelViewSet`，已有 `destroy`，`required_operations` 含 `'destroy': 'manage_assets'`。
- `DataScopeMixin` 已按角色对 `get_queryset()` 过滤；自定义 action 的权限由 `required_operations[action]` 决定。

## Goals / Non-Goals

**Goals:**
- 资产列表、固定资产表都能勾选多条并一次性删除。
- 资产列表复用既有选择；固定资产表补齐选择。
- 批量删除权限与单删一致（`manage_assets`），并受数据范围隔离。

**Non-Goals:**
- 不做跨页/跨加载的选择记忆（仅当前已加载列表中的选中项）。
- 不做批量删除的撤销/回收站（与单删同为硬删除）。
- 不改单删行为、不调整 `manage_assets` 的既有授权范围。
- 不设批量删除硬上限（`queryset.delete()` 可处理当前规模）。

## Decisions

### 决策 1：后端用专用 `batch_delete` action（POST，ids）
- **做法**：两 ViewSet 各加 `@action(detail=False, methods=['post'])` 的 `batch_delete`，接收 `{ ids: [...] }`；`get_queryset().filter(id__in=ids).delete()`（事务内），返回 `{ deleted: <count> }`。
- **理由**：一次请求、原子；`get_queryset()` 自动套用 `DataScopeMixin` 数据范围过滤，越权 id 自然被排除；与既有 `destroy` 权限模型一致。
- **备选**：前端循环调单删——N 次请求、非原子、易部分失败，**否**。

### 决策 2：权限 = manage_assets（与单删一致）
- **做法**：两 ViewSet 的 `required_operations` 加 `'batch_delete': 'manage_assets'`；前端批量删除入口用 `canManageAssets` 网关。
- **理由**：批量删除是更高危的单删集合，权限不应低于单删；保持一致、可预期。

### 决策 3：选择范围 = 当前已加载列表
- **做法**：沿用 `AssetList` 既有 `selectedAssets` 语义（当前页/当前筛选结果中的勾选项）；`FixedAssetList` 新增等价的当前列表选择。
- **理由**：与既有批量打印/调拨行为一致，避免跨页状态复杂度。

### 决策 4：确认弹窗显示数量；删除后刷新 + 清空选择
- **做法**：点「批量删除」→ `ElMessageBox` 二次确认（文案含删除数量）→ 调接口 → 成功提示 → 刷新列表 + 清空已选。
- **理由**：批量删除不可恢复，需显式确认与数量提示。

## Risks / Trade-offs

- **[误删不可恢复]** 批量硬删除无回收站 → **缓解**：二次确认 + 显示数量 + 仅 `manage_assets` 角色可见入口。
- **[越权删除]** 用户提交含他人/他区资产 id → **缓解**：`batch_delete` 基于 `get_queryset()`（DataScopeMixin），越权 id 被过滤排除，不会删除。
- **[跨页选择缺失]** 仅当前列表选中，跨页不累积 → **缓解**：与既有批量行为一致，文案不承诺跨页。
- **[大量删除性能]** 一次提交过多 id → **缓解**：`queryset.filter().delete()` 为单条 SQL，当前规模无虞；如需可后续加上限。

## Migration Plan

1. 后端：两 ViewSet 加 `batch_delete` + 权限映射，**无 DB 迁移**。
2. 前端：`api/assets.ts` 加两个 helper；`AssetList.vue` 批量栏加按钮；`FixedAssetList.vue` 加多选 + 批量栏 + 按钮。
3. 部署即生效，无需数据变更。

## Open Questions

1. 是否需要批量删除数量上限或改为软删除？默认**无上限、硬删除**（与单删一致）。
