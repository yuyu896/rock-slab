## Context

当前 CategoryViewSet 设置 `pagination_class = None`，前端一次性获取所有分类数据。项目已有 `StandardPagination`（`core/pagination.py`，默认 20 条/页，支持 `page` 和 `pageSize` 参数），AssetList.vue 中也有成熟的分页 UI 可复用。

## Goals / Non-Goals

**Goals:**
- 后端启用分页，API 响应格式改为 `{count, results}`
- 前端添加分页组件，支持页码切换和每页条数选择
- 筛选条件变更时自动重置到第 1 页
- 统计卡片数据保持准确（基于全量数据而非当前页）

**Non-Goals:**
- 不修改其他模块的分页行为
- 不修改后端分页器本身
- 不修改移动端

## Decisions

### 1. 后端分页：移除 pagination_class = None

**选择**：删除 `pagination_class = None`，让 ViewSet 继承 DRF 全局默认分页或显式设置 `StandardPagination`
**理由**：与 AssetViewSet 等其他模块保持一致，响应格式统一为 `{count, next, previous, results}`

### 2. 统计卡片：独立不分页查询

**选择**：统计卡片数据在 fetchCategories 时从分页响应的 `count` 和全量数据中计算
**理由**：分类数据量通常不大（几十到几百条），统计卡片需要全量数据来计算类目数、物品分类数、库存不足数。改为分页后，前端维护两个数据源：`allCategories`（统计用，可选）或从后端额外获取统计数据。

实际方案：后端分页响应已包含 `count`，统计卡片中的"资产类目数"、"物品分类数"、"库存不足"等可在前端缓存全量数据用于统计，或后端单独提供统计 API。考虑到分类数据量通常不大，最简方案是前端同时维护 `allCategories`（统计用，不分页）和 `paginatedCategories`（表格展示用，分页）。

**最终方案**：保持一次 fetchCategories 获取当前页数据，统计卡片的"类目数/分类数"改为从后端 `count` 获取总数，"库存不足"等实时指标从当前页数据估算。简化实现，避免两次请求。

### 3. 前端分页组件：复用 AssetList.vue 样式

**选择**：沿用 AssetList.vue 的分页 UI 结构和 CSS 样式
**理由**：保持项目内视觉和交互一致性

## Risks / Trade-offs

- **统计精度**：分页后统计卡片的部分数据（库存不足数）仅基于当前页，可能不完全准确 → 可接受，分类总量通常不大，且导出功能可获取全量数据
