# 实例点选器去重与收口 — 技术设计

## Context

InstancePicker 是绑定类单据（领用/调拨/回收/归还）明细行的实例点选组件：按 品目×合法前置状态×分公司 拉候选（pageSize=100），checkbox 多选，勾选集经 v-model（uuid 数组）上行，数量与勾选数联动。两个缺口：

1. 候选拉取只按行上下文过滤，无跨行排除 → 同一实例可在多行重复勾选（后端 ledger 单内重复引用终检兜底，提交时 400）。
2. `expanded` 是组件私有 ref：勾选不收起、多行面板可同时展开。

## Goals / Non-Goals

**Goals:**

- 候选排除本单他行已选实例（取消勾选/删行即回候选）
- 面板「完成」收起 + 同屏至多一个面板展开

**Non-Goals:**

- 不改一行多台多选与数量联动契约
- 不动后端（重复引用终检保留为兜底）
- 不改移动端（MobileAssign 等另有交互，本次只收 PC 创建页）

## Decisions

### D1：排除集合由编辑器汇总下传，点选器只做过滤

`TransferLinesEditor` 以 computed 汇总全行 `instances[].id` 为扁平 Set，经新 prop `excludedIds: string[]` 传入每行 InstancePicker；组件渲染候选时 `options.filter(o => !excludedIds.includes(o.id) || modelValue.includes(o.id))`——他行已选剔除、本行已选保留（勾选回显需要）。不放后端过滤参数：排除集合是**草稿态**（随勾选即时变化），后端列表接口无此语义，前端过滤最贴切；pageSize=100 的候选规模下性能无虞。

### D2：expanded 升为 v-model，互斥由编辑器协调

InstancePicker 的 `expanded` 改为 `v-model:expanded`（props+emit），面板加「完成（N 台）」按钮置 false 收起。编辑器持 `expandedRow: number | null`（行 key 或索引，用行 draft.key 更稳——索引在删行后会错位），传给每行 `:expanded="expandedRow === draft.key"` 并监听更新：某行展开即把 `expandedRow` 置该行 key（其余行自动收起），收起即置 null。不引入 provide/inject 或全局状态——两层组件直传足够。

### D3：收起后的回显沿用既有 picked-meta

收起后格子显示「已选 N 台」按钮（组件内既有）+ 编号回显（编辑器既有 `draft.instances.map(i => i.code).join('、')`），无新增回显逻辑。

## Risks / Trade-offs

- [行 key 用索引会因删行错位] → 用 `draft.key`（emptyDraft 已生成稳定 key）
- [被排除实例与本行已选的边界] → 过滤条件含 `|| modelValue.includes(o.id)` 保证回显勾选不丢；测试覆盖
- [候选 >100 台时排除后翻页缺失] → 既有 pageSize=100 限制先维持（超量品目本就少见），不在本次扩

## Migration Plan

纯前端组件改动，随下次部署的前端构建生效；无数据、无回滚风险。

## Open Questions

（无）
