# 打印弹窗三段式布局 — 技术设计

## Context

`AssetPrintDialog.vue` 弹窗当前整窗滚动（`.modal-content { max-height: 90vh; overflow-y: auto }`），footer（关闭/导出图片/打印）与 header（纸型切换）都在滚动流内。批量打印 100 条时预览约 7 屏，操作按钮被推到最底。项目内 `ApprovePreviewDialog`、`AdjustRecordsDialog`、`InventoryReport` 已采用三段式（仅 body 滚动），本弹窗为唯一异类。

## Goals / Non-Goals

**Goals:**

- 仅标签预览区滚动；纸型切换与底部操作按钮常驻可见。
- 打印输出与现状等价（块级文档流，多页分页行为不变）。

**Non-Goals:**

- 不动其他弹窗的滚动模式。
- 不做「按筛选全量打印」增强（勾选仍限当前页）。

## Decisions

### D1：flex 三段式，而非 footer sticky

```css
.modal-content { …; max-height: 90vh; display: flex; flex-direction: column; }  /* 去掉 overflow-y: auto */
.modal-header, .modal-footer { …; flex-shrink: 0; }
.modal-body { padding: 24px; flex: 1; min-height: 0; overflow-y: auto; }
```

理由：与项目内三个弹窗的既有模式一致；header 也一并常驻（切纸型不用回顶）；flex 布局下 footer 不会被内容穿透，无需 sticky 方案的遮挡背景色补丁。
备选 `footer position: sticky; bottom: 0` 改动更小，但 header 仍滚走、滚动条贯穿全窗、与项目惯例相悖，弃。

### D2：打印态显式复位为块级文档流

`@media print` 在既有规则上补：

```css
.modal-content { …; display: block; }      /* 解除 flex column */
.modal-body { padding: 0; overflow: visible; }  /* 解除滚动容器 */
```

理由：浏览器打印对 flex 子项与 overflow 容器的分片（fragmentation）支持不稳，A4 多页场景有被裁风险；显式回到与现状完全相同的块级流，打印行为零回归。这是本改动最大的风险点，用源码契约测试钉死。

## Risks / Trade-offs

- [源码契约断言较脆（改格式会红）] → 该测试文件已依赖 `?raw` 源码断言（@page、break-after 等先例），红了即提示同步改断言，属预期维护成本。
- [jsdom 测不了真实滚动布局] → 布局正确性靠手验清单（弹窗内滚、按钮常驻）+ 打印态靠源码断言。

## Migration Plan

纯前端 CSS，随常规发版；回滚无风险。

## Open Questions

（无——方案 A 已与用户对齐。）
