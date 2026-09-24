## Context

InstancePicker 现有两种模式：single（领用行用——点选即定并收起，换选非追加）与多选（归还/调拨/回收用——展开面板勾选、底部「完成」收起）。TransferLinesEditor 实例行数量输入已 `:disabled`（随勾选台数联动）。生平是行编辑弹窗（el-dialog 920px，左编辑右生平双栏）的右栏，类型列渲染 `row.actionType` 英文原值；constants 的 `TRANSFER_TYPES` 已有五类中文标签与配色。

用户拍板（2026-09-24）：全部统一单选点选即定；多选删除；生平类型中文化；弹窗扩大。

## Goals / Non-Goals

**Goals:**

- 四类创建页实例行统一单选（点选即定收起），一行一台、多台加行
- 多选模式与「完成」按钮从组件中删除（死代码不留）
- 生平类型中文标签；弹窗 920→1160

**Non-Goals:**

- 后端 API 契约（多实例行仍合法——导入等程序化路径照旧）
- 移动端（领用已是单选；其余移动端无实例点选）
- 单据明细行表格展示（TransferLinesTable 的实例 chip 列不变——展示与录入是两回事）

## Decisions

### D1：单选成为 InstancePicker 唯一形态，组件瘦身

删除 `single` prop 与多选分支（checkbox、「完成」按钮、已选计数文案的多选形态），点选即触发 `update:modelValue=[id]` + `change` 并收起。跨行去重（excludedIds）照旧——单选同样要排除他行已选。触发文案统一「点选实例 / 已选 1 台」。
- 备选：保留双模式按类型开关——留一条永不走的路给未来？否决：多选的痛点（长列表滚选）不会回来，留着是维护负担。

### D2：一行一台，数量自动=1

TransferLinesEditor 实例行：`onInstancesChange` 单选回调置 `instances=[选1台]`、`数量=1`（数量输入已禁用，展示随动）；多台回收/调拨=「+添加行」多次。校验 `instances.length === 数量` 退化为恒真（保留断言不动，防御未来）。回收处置向的在库/在用双态候选（recovery-stock-source-and-cleanup）在单选列表中照旧可选。
- 领用行的「一行一使用人一实例」语义不变（本就是单选）。

### D3：生平类型中文 + 弹窗加宽

类型列改 `TRANSFER_TYPES[row.actionType]?.label ?? row.actionType`（未知类型兜底原值，防御存量脏数据）；行编辑弹窗 width 920px→1160px（`top` 维持 6vh，内容区自适应），生平表格五列受益于增宽。

## Risks / Trade-offs

- [批量回收 N 台需 N 行操作] → 每台两击（加行+点选）vs 多选的滚选+完成；业务高频是 1~5 台，点选路径更短；真出现百台批量场景时再立「批量圈选」专项（不做勾选复活）
- [删除多选后未知调用方] → grep `single`/多选 API 仅 TransferLinesEditor 一处消费；组件为内部组件无外部引用
- [弹窗 1160 在小屏溢出] → el-dialog 自带超宽回退（max-width 90%+ 居中），实际项目页面基准 1600px（transfer-detail-width-1600 先例），1160 安全

## Migration Plan

纯前端，无迁移。部署常规 deploy.sh；手验四类创建页点选与生平展示。

## Open Questions

（无——两条均用户拍板，尺寸取保守 +240px。）
