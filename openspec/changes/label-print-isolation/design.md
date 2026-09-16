# 设计：标签打印输出隔离

## Context

`AssetPrintDialog.vue` 目前内联在 `FixedAssetList.vue` 模板里（`#app` > MainLayout > 页面 > 弹窗），点「打印」直接 `window.print()`。全站无 `@media print` 样式，浏览器把整个 DOM 当打印源，输出侧边栏、顶栏、表格和弹窗控件；弹窗容器 `max-height: 90vh; overflow-y: auto` 还会把超出一屏的标签裁掉。深色模式下弹窗文字/边框用的是浅色 CSS 变量，打印到白纸上会看不清。

## Goals / Non-Goals

**Goals:**

- `window.print()` 的输出只含标签网格，不含应用壳与弹窗控件
- 任意数量标签跨页完整输出，单个标签不被页边界切断
- 打印输出为白底黑字的打印友好配色，与深色模式无关
- 屏幕上的弹窗预览行为不变（现有测试不回归）

**Non-Goals:**

- 不改标签内容口径（品目编号 → 内部编号是下一条提案）
- 不做标签纸规格预设（40×30 等）、@page 尺寸定制保持默认页边距的轻量调整
- 不引入 iframe 打印方案或新增依赖
- 不改后端

## Decisions

**D1：Teleport 到 body 的独立打印根，而非 visibility 隐藏技巧**

把弹窗整体 `<Teleport to="body">`，与 `#app` 平级。全局打印规则只需一条 `@media print { #app { display: none !important } }`。

- 备选「`body * { visibility: hidden }` + `#print-area` 绝对定位」的经典配方：隐藏元素仍占版面，页面高度大时可能产出空白尾页，且 `position: fixed` 元素（侧边栏类）在部分浏览器每页重复，均需逐个补丁。
- 备选「iframe 打印」：隔离最彻底，但要维护两份 DOM/样式注入，代码量与本项目朴素风格不成比例。
- Teleport 方案 DOM 结构一变（弹窗挪出 `#app`），CSS 一条规则完成隔离，无 hack。Element Plus 的浮层同样挂 body，但打印时本弹窗是唯一打开的浮层，无干扰。

**D2：打印态样式全部收在组件内（含 `#app` 隐藏规则）**

- 组件 scoped `@media print`：`.modal-overlay` 转静态定位去遮罩、`.modal-content` 去 `max-height`/`overflow`/边框圆角、`.modal-header`/`.modal-footer` `display: none`、`.print-label` `break-inside: avoid`、配色改白底黑字灰边框的固定值（不走 CSS 变量，绕开深色模式）。
- `#app { display: none !important }`、`body` 白底、`@page { margin: 8mm }` 放组件内**非 scoped** 样式块：本组件是全站唯一 `window.print()` 调用方，规则随组件走、不污染 `global.css`；规则仅作用于打印媒体，对屏幕渲染零影响。
- 备选「规则进 `styles/global.css`」：同样可行，但全局样式袋会随打印源增多而膨胀，且测试需引 `@types/node` 读文件（css `?raw` 在 vitest 返回空串）；组件持有后 `.vue?raw` 源码断言即可覆盖。

**D3：沿用 `window.print()`，不加打印态 JS 编排**

打印态完全由媒体查询驱动，无 `beforeprint`/`afterprint` 事件监听和 body class 切换，打印后无状态需要清理。

**D4：测试取可断言子集**

jsdom 不应用媒体查询，无法直接断言打印样式。测试断言：弹窗内容 Teleport 到 body（`#app` 之外）、标签条数与文案（编号/名称/分公司）、「打印」按钮触发 `window.print`。CSS 规则本身以代码评审 + 浏览器实测覆盖。

## Risks / Trade-offs

- [Teleport 后弹窗 z-index 层级变化，被其他同时打开的浮层盖住] → 弹窗 overlay `z-index: 200` 保留，实测当前页面无并存浮层场景
- [浏览器打印"背景图形"默认关闭，标签边框仍会打印（border 非 background）] → 边框用 border 而非 background 实现，不受该开关影响
- [jsbarcode 在 Teleport 内的渲染时机] → 现有 `watch(visible) + nextTick` 渲染逻辑不变，Teleport 不改变挂载时序
