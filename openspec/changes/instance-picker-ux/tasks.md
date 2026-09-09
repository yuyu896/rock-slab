# 实例点选器去重与收口 — 实施任务

## 1. 跨行去重

- [x] 1.1 `InstancePicker.vue` 加 `excludedIds?: string[]` prop，候选渲染过滤 `!excludedIds.includes(o.id) || modelValue.includes(o.id)`（他行剔除、本行已选保留）
- [x] 1.2 `TransferLinesEditor.vue` computed 汇总全行 `instances[].id`，逐行下传（本行已选天然满足保留分支，无需按行剔除自身）

## 2. 面板完成即关 + 互斥展开

- [x] 2.1 `InstancePicker.vue`：`expanded` 升级 `v-model:expanded`（defineModel 或 props+emit）；面板加「完成（N 台）」按钮置收起
- [x] 2.2 `TransferLinesEditor.vue`：持 `expandedRow`（按 `draft.key`），行展开即独占、收起置 null；勾选/取消不强制收起（多台场景连续勾选）

## 3. 测试与验证

- [x] 3.1 vitest：跨行去重（行 2 候选不含行 1 已选；取消/删行回候选；本行已选保留勾选）
- [x] 3.2 vitest：完成收起 + 同屏互斥（展开行 2 时行 1 面板消失；一行勾 3 台数量联动不回归）
- [x] 3.3 `npm run build` 类型门通过；vitest 全绿
- [x] 3.4 本地浏览器手验：领用页两行同品目——行 2 候选不含行 1 已选实例、展开互斥（全页单面板）、完成按钮收起、数量随勾选联动（造数走台账调整单补在库底数）
