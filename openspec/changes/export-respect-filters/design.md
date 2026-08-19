## Context

- 导出链路：页面 `handleExport` → `api/*.ts` 的 `exportXxx(params)`（GET blob）→ 后端 `@action export_excel` 内 `self.filter_queryset(self.get_queryset())`。后端与列表共用同一 filterset，**参数到了后端就生效**。
- 现状缺口（逐页核对源码）：
  - `AssetList.vue` handleExport 仅传 `branch`；页面筛选有 branch/category/status/keyword
  - `FixedAssetList.vue` handleExport 传 branch/status/keyword；页面筛选还有「资产名称」（后端 `FixedAssetFilterSet` 支持 `资产名称` 字段过滤）
  - `useTransferList.ts` handleExport 传 type/fromBranch/toBranch/status；页面筛选还有 keyword（后端 TransferFilterSet 支持）
  - `AssetSummary.vue`（branch/category/keyword）、`Category.vue`（资产类目/keyword）已完整
- 旧页 `Purchase.vue` 的导出仅传 type，但路由 `/assets/purchase` 无菜单入口（侧边栏指向 `/transfers/purchase` 即 PurchaseList，走 useTransferList）。

## Goals / Non-Goals

**Goals:**
- 已有导出的 8 类页面（明细/固定资产/汇总/品目/采购/领用/调拨/回收）导出数据集与当前筛选一致（所见即所得）。
- 以测试固化该行为，防止后续页面加筛选时再漏。

**Non-Goals:**
- 不给无导出的页面（盘点/用户/组织/审计/报表）新增导出。
- 不改导出列、文件名、格式；不加导出前的确认弹窗。
- 不动遗留路由 `/assets/purchase`（Purchase.vue）。

## Decisions

### D1. 只改前端参数透传，后端零改动
**选择**：三处 `handleExport` 补传漏掉的筛选参数（空值仍 `|| undefined` 不传，与现有风格一致）；`api/assets.ts` 的 `exportAssets` 参数类型从 `{ branch?: string }` 放宽为含 category/status/keyword 的 Record。
**依据**：后端 export 均已 `filter_queryset`（assets×3 / categories / transfers 逐一核对过），与列表完全同路径；后端已有 list 筛选测试覆盖 filterset，无需重复实现。

### D2. 参数映射表（唯一事实来源）

| 页面 | 导出应传参数 |
|---|---|
| 资产明细 | branch, category, status, keyword |
| 固定资产 | branch, status, keyword, 资产名称 |
| 采购/领用/调拨/回收 | type（页面固有）, fromBranch, toBranch, status, keyword |
| 资产汇总 | branch, category, keyword（现状已满足） |
| 品目 | 资产类目, keyword（现状已满足） |

### D3. 测试策略：前端断言调用参数为主，后端补少量端点级回归
**前端**（vitest，@vue/test-utils）：对 AssetList/FixedAssetList 挂载后设筛选、触发导出，断言 `exportAssets`/`exportFixedAssets` 收到全量参数；对 `useTransferList` 组合函数直接断言 `exportTransfers` 参数（组合函数级测试比挂载四个页面更省）。
**后端**（pytest）：补 2 个端点级用例——`GET /api/assets/export?branch&category&keyword` 与 `GET /api/transfers/export?type=recovery&keyword` 断言结果集被过滤（防止未来有人把 export 改成不过滤）。

### D4. 旧页 Purchase.vue 不改
无菜单入口的遗留路由，改它无收益；将来若清理死路由一并删除。

## Risks / Trade-offs

- [筛选后结果为空时导出空表] → 与"所见即所得"语义一致，可接受；不额外拦截。
- [keyword 触发后端 icontains 全表扫] → 与列表查询同路径同代价，导出为低频操作，可接受。
- [用户以为导出是全量数据] → 导出成功提示维持现状，本变更语义即"所见即所得"。

## Migration Plan

纯前后端代码变更，无迁移。`deploy.sh` 常规部署，回滚 git revert。

## Open Questions

（无——范围与语义均已确认。）
