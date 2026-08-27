## Context

修订 1.2（设计书 2026-08-27 修宪记录）落在盘点任务详情页与盘点只读接口上。现状：

- `views/Inventory.vue:422-521` 详情视图仅 基本信息/盘点统计/盘点规则 三张卡；「导出报告」（:432-439）与「继续盘点」（:440）两个按钮均无 `@click`，为死按钮；继续盘点有效入口在任务列表行（`InventoryTaskList.vue:188-189` 重盘按钮）。
- 报告弹窗 `InventoryReport.vue` 已展示 items 明细表（编号/名称/应盘/实盘/变动/结果），数据来自 `GET /api/inventories/{id}/report`（views.py:313-329，返回 task + progress + items + adjustments 计数，items 全量不分页）。
- `checks` 接口（views.py:331-345）分页返回 InventoryCheck，但序列化器只回 UUID 外键（task/item/stock/checked_by），无姓名与品目信息——PC 端无法直接展示；手机扫码页 `MobileScan.vue:407-415` 最近记录引用的 `scan.code/name/result/time` 字段序列化器根本不返回，当前渲染为空白。
- 后端有盘点模板下载/结果导入（`download_template` / `import_result`，openpyxl），无报告导出接口。
- `LedgerAdjustment` 有 `单据编号`（唯一单号），盘点任务经 related_name `adjustments` 关联其差异调整单——导出"所生成调整单号"的数据源就在手边。

## Goals / Non-Goals

**Goals:**
- 详情页能看到物品明细（品目、应盘、实盘、差异、结果、备注，差异带标记）。
- 详情页能看按人盘点流水（每次提交一条），支持按盘点人筛选（"每个员工的盘点表"）。
- 「导出报告」一键下载 Excel：基本信息 + 统计 + 明细 + 所生成调整单号。
- 详情页无死按钮；手机扫码页最近记录字段对齐，消除空白渲染。

**Non-Goals:**
- 不动盘点范围模型（库别维度/实例盘，第 6 案）。
- 不改报告 JSON 接口既有字段语义（adjustments 计数结构不变）；不做报告弹窗改版。
- 不为流水做按人汇总统计（每人次数/最后时间），修订要求的是逐条流水按人查看。
- 死按钮只清详情页两处，不排查全站其他无绑定控件。

## Decisions

### D1：明细表复用报告接口，详情页进入改拉 report 一次取全
`viewTask` 现拉 `progress` 接口；改为拉 `report` 接口（其 progress 字段同构），一次取得 task/progress/items/adjustments，明细表直接渲染 `items`。不新增 items 接口——报告弹窗与详情页同源同口径，避免两套明细数据不一致。未开始任务 items 为空 → 明细卡空态文案「盘点开始后生成物品清单」。明细表置于三张信息卡下方，朴素表格 + 容器限高滚动（复用 `InventoryReport` 的 report-table 样式风格），差异列沿用报告弹窗的正负着色（盘盈绿/盘亏红），不加徽章。

### D2：按人流水 = checks 接口 + checked_by 过滤 + 展示字段补齐
后端 `checks` action 增 `checked_by`（UUID，可选）过滤参数；`InventoryCheckSerializer` 增三个只读展示字段：`checked_by_name`（`checked_by.name`）、`asset_code` / `asset_name`（`stock.item.*`），存量字段不动（增量，无消费方破坏）。前端详情页新增「盘点流水」卡：筛选下拉（全部 + 盘点人）+ 朴素表格（时间、盘点人、资产编号、资产名称、数量、设备），`pageSize=100` 分页拉取。修订原文"支持按盘点人分组查看"以筛选下拉实现——比分组行更贴 Excel 筛选习惯（与列表页分公司筛选交互一致），逐人筛出即"每个员工的盘点表"。备选（后端按人聚合接口）被弃：需求是逐条流水非汇总，且多一次接口无增益。

盘点人下拉选项由已加载的流水行前端聚合（去重 checked_by_name）。限制：总条数超一页且某人全部流水在后续页时首屏下拉缺人 → 翻页后选项随数据补全；单任务参与盘点者个位数的实际场景下首屏即覆盖。

### D3：报告导出走独立 action，openpyxl 双 sheet，任意状态可导
新增 `GET /api/inventories/{id}/export-report`（detail action，无操作码要求，DataScope 过滤，与 `download_template` 同权限面）。工作簿两 sheet：
- 「盘点报告」：基本信息区（任务名、分公司、类目、状态、创建人、创建/开始/提交/完成时间、漏盘/重复规则）→ 统计区（应盘/已盘/正常/盘盈/盘亏/未盘 + 正常/盘盈/盘亏率）→ 调整单区（单据编号、目标列、变动量、事由、经办人、创建时间，取 `task.adjustments`；非 completed 任务该区输出一行"无（任务未完成）"）。
- 「盘点明细」：序号、资产编号、资产名称、资产类目、应盘、实盘、差异（带 +/- 号）、结果、盘点人、盘点时间、备注。

差异在 Excel 中以正负号 + 结果文字呈现，不做单元格上色（朴素导出，与现有导出一致）。文件名 `盘点报告_{task.name}.xlsx`，Content-Disposition 写法沿用 `download_template`。不限状态：in_progress 导出即当前进度快照（中期留档有实用价值），未开始导出空明细报告。备选（仅 completed 可导）被弃——修订未设限，且驳回重盘过程中留档对比是真实诉求。

### D4：死按钮清除 + 手机端字段对齐
删 `Inventory.vue:440`「继续盘点」按钮（样式类一并清理）；「导出报告」绑定 `exportInventoryReport`（blob 下载，模式照抄 `downloadTemplateAction`，含 loading 态）。`MobileScan.vue` 最近记录改用新展示字段渲染（asset_code、asset_name、qty、checked_at、checked_by_name），删除对不存在字段（code/name/result/time）的引用——`result` 徽标逻辑不重建（result 挂在 InventoryItem 不在 check 记录上，逐条流水无需结果标记）。写入规范：详情页操作控件必须有有效绑定或删除。

## Risks / Trade-offs

- [大任务 items 全量返回/全量渲染（分公司×品目数百行）] → 报告接口现状即全量（不改）；明细表容器限高滚动；导出为一次性内存生成，千行级 xlsx 无压力。
- [checks 超一页时下拉缺人（见 D2）] → 服务端按 checked_by 过滤保证分页正确；选项随翻页补全；实际多人盘点规模远小于一页。
- [导出与报告弹窗数据口径漂移] → 同一 viewset 内同源查询（task.items / task.adjustments），无第二套口径。
- [中文字段/姓名在 Excel 列宽挤压] → 与现有导出一致不设列宽，用户打开自行调整；不为此引入样式逻辑。

## Migration Plan

纯增量（新 action + 序列化器增量字段 + 前端视图改造），无模型/迁移/数据变更，无部署顺序要求。回滚 = revert 提交。

## Open Questions

（无——修订 1.2 已定案，实现口径如上。）
