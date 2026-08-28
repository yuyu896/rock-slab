## 1. 后端：消耗统计接口

- [x] 1.1 `apps/reports/views.py` 新增 `consumables` 视图：assign+已通过+consumable 明细行，TruncMonth 按月、部门×品目分组 Sum，Python 侧透视（months/rows/grandTotal），dateRange 与 branches 筛选，`_scope_queryset(from_branch)` 范围过滤，空部门归「未归属」
- [x] 1.2 `apps/reports/urls.py` 注册 `consumables/` 路由
- [x] 1.3 pytest：部门×月份×品目聚合、非消耗品行/未生效单据不计入、未归属分组、dateRange+branches 筛选、越权 branches 交集拦截、范围受限用户只见本公司

## 2. 前端：消耗统计标签页

- [x] 2.1 `api/reports.ts` 加 `getConsumptionReport` 与类型（months/rows/grandTotal）；`types` 补类型定义
- [x] 2.2 `Reports.vue` 新增"消耗统计"tab：Excel 式朴素表（部门/编号/名称/单位/各月/合计/总计行），随页顶 branches+dateRange 筛选联动，空态提示
- [x] 2.3 导出报表按钮追加"消耗统计" sheet（列与页面一致）
- [x] 2.4 vitest：行/总计渲染、月份列展开、空态；`npm run build` 通过

## 3. 验证与收尾

- [x] 3.1 后端 `pytest` 全绿；前端 `npm run build` + vitest 全绿
- [x] 3.2 本地实测：造消耗品采购+领用流水（走单据），报表页验证分组与月份展开；无授权账号验证范围隔离
- [x] 3.3 更新 `docs/design/v2-revision-draft.md` 拆案表第 10 案状态（含第 8 案备注行随行提交）；feat + openspec 两个 commit → push
