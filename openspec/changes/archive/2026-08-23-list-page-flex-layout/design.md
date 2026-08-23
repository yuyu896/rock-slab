## Context

MainLayout 现状：侧栏 fixed 定高 100vh，`.main { min-height: 100vh }`，`.content { flex: 1; overflow-y: auto; padding: 24px }` 是整页滚动容器。列表页各自为政：

- 资产明细/固定资产/资产汇总三页：表格容器写死 `max-height: calc(100vh - 340px)`，340 是头部+筛选+分页的经验估值，随区块增减即漂移；
- 四类流转单/类目/审计日志/盘点/采购页：无高度管理，整页滚动，分页在文档流末尾，屏高不足时需滚到底才能翻页；
- 部分表格容器 `overflow: hidden`，无 sticky 表头。

技术约束：纯 CSS + 自定义属性（无 Tailwind）；`.content` 同时服务列表页与非列表页（工作台、新建、详情），不能要求所有页面一次性改造。

## Goals / Non-Goals

**Goals:**
- 列表页在任意屏高下占满内容区：表格撑满剩余高度、表头滚动常驻、分页钉底贴边；
- 消除 `calc(100vh - 340px)` 类魔法数字，高度全部由 flex 派生；
- 非列表页行为完全不变（内容超高仍滚动）；
- 列表页默认每页 50 条。

**Non-Goals:**
- 不改后端分页（`StandardPagination` 默认 20、上限 100 保持）；
- 不动 Reports/Dashboard/Organization（组织页已有 `height:100%` 自管布局）与移动端；
- 不重做任何页面的信息结构（那是 P2 单据明细行化的事）。

## Decisions

### D1 骨架：`.main` 定高 + `.content` flex 列 + 全局 `.page-fill` 工具类

- `.main`：`min-height: 100vh` → `height: 100vh`。侧栏本就是 fixed 100vh，main 无需随内容长高；定高让 `.content` 高度确定，flex 派生才有依据。
- `.content`：加 `display: flex; flex-direction: column;`，保留 `overflow-y: auto`。
- `styles/global.css` 加两条规则：
  - `.content > * { flex-shrink: 0; }` —— 默认所有页面根节点不可压缩：非列表页自然高度超出时 `.content` 照旧整页滚动，行为与今天一致；
  - `.page-fill { flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; }` —— 列表页根节点显式声明占满（`min-height: 0` 允许其收缩、交给页内表格滚动）。

**替代方案**：给每页写死 `height: calc(100vh - Npx)`（新魔法数字，否决）；或 `.content { overflow: hidden }` 且所有页面自管滚动（侵入全部 40+ 页面，本小案否决，P2 视需要再评估）。

**为何工具类放 global.css 而非 MainLayout scoped**：`.page-fill` 被各页面组件使用，属跨组件契约；且 `.content > *` 选择器需命中路由页根节点，scoped 样式对 slot 内容不可靠。

### D2 页内分工：头/筛选拒绝压缩，表格 `flex: 1` 内滚，分页 `flex-shrink: 0`

- 页面头部、筛选区、统计卡：`flex-shrink: 0`（显式声明，防矮屏被压扁）；
- 表格容器：`flex: 1; min-height: 0; overflow: auto`（横纵均可滚），`max-height` 删除；
- 表头：`thead th { position: sticky; top: 0; background: … }`（滚动容器是表格容器，sticky 相对它生效；已有 sticky 的三页不动）；
- 分页条：`flex-shrink: 0`，天然钉底（表格 flex:1 撑满后分页即贴内容区底边）。

### D3 多视图页（盘点管理、采购入库）的处理

根节点同样加 `.page-fill`，但额外 `overflow-y: auto`：列表子视图 `flex: 1; min-height: 0` 精确填满（无根滚动）；切到详情/新建等自然高度子视图时，由页根滚动。子视图根节点默认 `flex-shrink: 0`（继承 D1 同一防御逻辑，写在各页 scoped 样式）。

### D4 默认每页 50：前端单方面改

`BasePagination` 默认 prop、`useTransferList`、各列表页初始 `pageSize`、Category 页自定义「每页条数」选择器默认值，统一 20→50。每页条数选项维持 `[10, 20, 50, 100]` 不变（用户仍可调回 20）。后端上限 100 ≥ 50，无兼容问题；未登录传参者仍拿后端默认 20，属预期。

### D5 范式统一而非逐页发明

所有列表页统一套同一结构：`根(.page-fill) → 页头/筛选(flex-shrink:0) → 表格容器(flex:1) → 分页(flex-shrink:0)`。后续 P2 台账主视图、单据明细行化直接复用该骨架，新列表页照抄即可——这是本小案作为「布局地基」的意义。

## Risks / Trade-offs

- [矮屏（<500px 高）下表格被头部/筛选拟压缩到很矮] → 表格容器保底 `min-height: 200px`，超出部分由 `.content` 兜底滚动（flex 布局自动溢出）。
- [`.content > *` 全局规则影响未知页面] → 该规则只声明 flex-shrink:0，与改造前「内容自然高度+容器滚动」语义等价；逐页走查 PC 端路由页确认。
- [sticky 表头背景透明导致滚动时行文字透出] → sticky th 必须带不透明背景（沿用现有 `--color-bg-elevated`）。
- [Category 页卡片视图与表格视图共用页面根] → 卡片视图容器同样给 `flex: 1; min-height: 0; overflow-y: auto`，两视图等价受益。
- [vitest 既有断言（AssetSummary pageSize:20）] → 随默认值同步更新为 50。

## Migration Plan

纯前端样式/默认值变更，无数据迁移。部署即生效；回滚即 revert 提交。验收：任意屏高（含缩放窗口）下各列表页表格撑满、分页贴底、表头滚动常驻；工作台/新建/详情页滚动行为与改造前一致。

## Open Questions

无——布局方案已在总设计书探索期定案（决策 #11 UI 风格与第八节前端规范）。
