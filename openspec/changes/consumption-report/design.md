## Context

第 8 案后消耗品领用即出账（在库−N、不进在用），领用明细行（部门 FK + 数量 + 品目 FK）即发放流水，但无聚合出口。reports 应用已有 5 个函数视图（overview/by_branch/by_status/by_category/transfers），统一走 `_scope_queryset` 数据范围过滤与 `dateRange`/`branches` 参数约定；前端 Reports.vue 已有标签页结构与 XLSX 导出模式。生产字典已切 157 个消耗品品目（2026-08-28）。

## Goals / Non-Goals

**Goals:**
- `GET /api/reports/consumables/`：部门 × 品目 分组、按月展开的消耗品发放数量汇总，现算聚合。
- Reports.vue 新增"消耗统计"标签页（Excel 式朴素表格），随页顶筛选联动，并入 Excel 导出。

**Non-Goals:**
- 金额折算（领用行无单价；按品目采购价派生待真实需求另立）。
- 资产报表排除消耗品（2026-08-28 拍板：不排除，口径与数量管理品目一致）。
- 按签字人（使用人）维度的统计（部门是成本中心；使用人是签字记录，需要时前端下钻单据列表即可）。
- 任何写路径、汇总表、定时物化（铁律 1：消耗数从单据行现算，不落第二份）。

## Decisions

### D1：函数视图 + 既有参数约定，不引入 ViewSet

与 reports 现有 5 个视图同构：`@api_view(['GET'])` + `IsAuthenticated`，权限模型沿用"所有登录用户可看、数据按范围隔离"。筛选参数复用 `dateRange`（YYYY-MM-DD,YYYY-MM-DD）与 `branches`（逗号分隔 id），解析直接用 `_parse_selected_branches` 与 transfers 报表同款日期解析，零新概念。

### D2：TruncMonth 聚合 + Python 侧透视

查询集：`TransferLine.objects.filter(transfer__action_type='assign', transfer__审批状态='已通过', item__management_type='consumable')`，月份键 = `TruncMonth('transfer__调拨日期')`（Django ORM 在 SQLite/PG 双后端均正确翻译，无手写 SQL）。`.values('department', 'month')` 分组 `Sum('数量')` 后在 Python 侧透视成 行（部门×品目）× 列（月份）。

响应形状：

```json
{
  "months": ["2026-08", "2026-09"],
  "rows": [
    {"department": "行政部", "code": "B-b00001", "name": "打印纸", "unit": "包",
     "quantities": {"2026-08": 8, "2026-09": 2}, "total": 10}
  ],
  "grandTotal": {"2026-08": 8, "2026-09": 2, "total": 10}
}
```

`months` 有序列表供表头渲染；`quantities` 缺月键视为 0。备选"前端拿扁平行自己透视"被否：透视逻辑单端一份，前端保持纯渲染。

### D3：口径细节三则

- **生效状态**：领用单生效值即 `'已通过'`（'已入库' 为采购单专用状态），单值过滤。
- **分公司归属**：领用单 `from_branch`（所属/发放方），`_scope_queryset(transfer_fields=('from_branch',))`——调出方是消耗发生地，调入方对领用单无语义。
- **空部门**：`department__name` 为 None → 「未归属」分组（历史/导入兼容）；分组键用 department id（跨分公司同名部门分行可辨，不合并），展示用名称。

### D4：前端一张朴素表 + 导出 sheet

Reports.vue 详情区新增 tab（与分公司报表等并列）：列 = 部门、品目编号、品目名称、单位、`months` 展开的各月数量…、合计；总计行置底；排序按后端返回（部门名、合计降序）。横向列多时容器横向滚动（既有表格样式行为）。现有"导出报表"按钮的 XLSX 工作簿追加"消耗统计"sheet（列与页面一致），复用既有 XLSX 工具链。分公司/时间筛选沿用页顶既有筛选器（已有 `branches` 多选与 `dateRange`），消耗统计 tab 读取同一筛选状态。

## Risks / Trade-offs

- [跨年时间跨度大 → 月列过多] → dateRange 收窄即可；默认展示全部月份属预期行为，表格横向滚动承载。
- [调拨日期为手填业务日期，可能晚于/早于实际操作] → 与 transfers 报表、盘点口径一致（业务日期优先），不引入 created_at 双口径。
- [部门字典变动（改名/删除）] → 部门 PROTECT 引用下删除受阻；改名随联查实时反映（现算聚合的天然优点）。
- [生产初期无数据 → 空表] → 空状态提示"暂无消耗品发放流水"，与既有报表空态一致。

## Migration Plan

纯增量（一个只读接口 + 一个前端 tab），无迁移、无部署顺序依赖。回滚 = 前端隐藏 tab + 后端路由摘除（或整体 revert，无数据影响）。

## Open Questions

无——口径已于 2026-08-28 与用户议定（数量先行、金额后置、报表不排除消耗品）。
