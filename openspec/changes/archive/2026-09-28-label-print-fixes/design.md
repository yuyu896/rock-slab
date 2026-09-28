# 标签打印弹窗缺陷修复 — 技术设计

## Context

标签打印弹窗（`frontend/src/views/assets/AssetPrintDialog.vue`）双通道架构：①浏览器打印（60×40 标签纸 / A4 双列，`@page` 随纸型由专属 style 元素改写）；②导出图片 PNG（`utils/labelImage.ts`，960×640，供汉印 M1 等 App 生态蓝牙标签机取图）。超宽行自适应缩号存在两条并行实现：打印通道 `fitLabelLines()`（读 DOM computed 样式，步进 -0.4px，下限 2.2mm）与导出通道 `fitLines()`（canvas measureText，步进 -0.1mm 按比例），参数同源（`LABEL_SPEC` ↔ 打印 CSS）。

现状缺陷（2026-09-28 审查确认）：

1. `switchPaper()` 在 `paper.value = size` 后**同步**调用 `fitLabelLines()`——Vue 的 DOM 更新是异步批处理，此刻标签仍挂旧纸型 class，字号与可用宽都按旧几何测量；随后 class 切换，新几何下超宽的行不再缩号，被 `.fit` 的 `overflow: hidden` 裁断。
2. `openExport()` 的 `catch {}` 空块：canvas 渲染失败时导出视图直接弹回，无提示、无日志。
3. `labelFileName()` 空内部编号产出 `标签_.png`；导出列表 `v-for :key="item.name"` 以文件名为键，两个空编号实例即键冲突。

打开弹窗的首条路径无恙：`watch(visible)` → `renderQrCodes()` 内有 `await nextTick()` 后才 fit。

## Goals / Non-Goals

**Goals:**

- 任意纸型、任意切换方向下，超宽行都按 2.2mm 下限缩号，打印输出不出现文本截断。
- 导出图片失败对用户可见、对排查可查（错误信息 + console.error）。
- 空内部编号实例可正常导出且无键冲突。

**Non-Goals:**

- 不改标签版式参数（`LABEL_SPEC` 与打印 CSS 的双份同源维持现状，仅有的对齐已逐项核对一致）。
- 不动「勾选限当前页 / 按筛选全量打印」增强（记忆中已提过、未立项）。
- 不动后端、不涉台账。

## Decisions

### D1：switchPaper 改 async，`await nextTick()` 后 fit（而非 watch(paper)）

```ts
async function switchPaper(size: PaperSize) {
  paper.value = size
  localStorage.setItem(PAPER_KEY, size)
  applyPageSize(size)
  await nextTick()   // 等 DOM class 换到新纸型
  fitLabelLines()    // 按新几何重算缩号
}
```

理由：与 `renderQrCodes` 已有的 nextTick 模式一致，改动最小、调用点单一。
备选「`watch(paper, async v => { applyPageSize(v); await nextTick(); fitLabelLines() })`」把三步聚拢一处更内聚，但引入新 watcher 且等价，不值得。用户连点两个纸型按钮时，每次切换各自 await 后 fit，最后一次生效，天然收敛。

### D2：导出失败——留在导出视图内显示错误态，而非弹回

`openExport` 的 catch 里不再 `exportMode.value = false`，改为置 `exportError` ref；导出视图渲染错误占位（文案如「标签图片渲染失败，请重试」+ 重试按钮复用 openExport）。同时 `console.error('标签图片导出失败', error)`。

理由：弹回打印视图让用户误以为按钮没反应；留在导出视图给出明确失败态，与打印通道 QR 失败占位（「QR 生成失败」）行为对称。重试按钮成本低（exporting 态已有）。
备选「引入 ElMessage.error」——组件目前零 Element Plus 依赖（纯原生 button/div），为一个 toast 破坏这点不划算。

### D3：空内部编号兜底——文件名用 id 短码，列表键改 id

- `labelFileName(asset)`：内部编号为空时回退 `` `标签_未编号_${asset.id.slice(0, 8)}.png` ``（LabelAssetShape 增加 `id?: string`）。
- `exportItems` 结构从 `{ url, name }` 扩为 `{ id, url, name }`，`v-for :key="item.id"`。

理由：id 是调用方必传的行键（FixedAssetList `toPrintShape` 已含），兜底不引入新依赖；id 截 8 位足够消歧且文件名可读。备选「直接跳过空编号实例的导出」会静默少出图，与 D2 的可见性原则相悖，弃。

## Risks / Trade-offs

- [jsdom 测不了真实 computed 样式] → D1 的防回归测试不测视觉，测时序契约：mock `nextTick`/微任务刷新后断言 `fitLabelLines` 在 class 更新之后执行（如 stub getComputedStyle 返回值随 class 变化，断言缩号用了新纸型字号）；辅以源码断言 `switchPaper` 含 `await nextTick()`（本组件测试已有 `?raw` 源码断言先例）。
- [labelFileName 兜底改变纯函数签名（加 id）] → 可选字段，现有调用点（测试断言文件名）不受影响；labelImage.test.ts 补空编号用例即可。
- [导出错误态文案误导用户自责] → 文案中性（「渲染失败，请重试」），不暗示操作错误。

## Migration Plan

纯前端展示层修复，随常规发版走 `bash deploy.sh`；无数据迁移、无回滚风险（回滚即恢复缺陷现状，无副作用）。

## Open Questions

（无——三处处置在提案阶段已与用户对齐方向：Bug 1 必修，2/3 顺手堵。）
