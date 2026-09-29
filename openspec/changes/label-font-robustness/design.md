# 标签字体根治 — 技术设计

## Context

台州个案（2026-09-29）：仅一台电脑打印预览裁掉 100+ 编号的末位。机制：`--font-mono` 依赖系统字体解析（无 @font-face，各机可不同）× 打印通道缩号零余量 × `.fit` overflow:hidden × NO 行 700 粗。任何机器的打印/屏显度量微差被放大成末位截断。

## Goals / Non-Goals

**Goals:** 任何电脑、任何浏览器、打印或屏显，标签文字渲染一致且不截断；编号/序列号在容量极限内信息完整。

**Non-Goals:** 不做超容量（>27~29 字符）换行布局（未触发，另行立项）；不改版式几何参数；不动 60×40/A4/导出三通道的布局规则。

## Decisions

### D1：`@fontsource/jetbrains-mono` 拉丁子集自托管（而非 vendor 手拷 woff2）

npm 包随构建走，`import '@fontsource/jetbrains-mono/latin-400.css'`（及 600/700）即在全局注册 `@font-face "JetBrains Mono"`（带 unicode-range 拉丁子集、woff2 由 Vite 哈希打包）。`--font-mono` 链表首位即命中已加载字体——屏显、打印预览、打印、PDF 全部同一字体文件。
备选「拷 woff2 进 src/assets + 手写 @font-face」：等效但手工维护字体文件与子集声明；备选「系统预装字体优先（Consolas）」：只换依赖不消除差异（Consolas 各 Windows 版本度量亦有差），弃。

### D2：缩号余量系数 0.97，两侧同参

打印通道：`fitLabelLines` 循环条件 `line.scrollWidth > line.clientWidth * FIT_SAFETY`（0.97）；导出通道：`computeLabelLayout` 调 `fitLines(..., labelTextWidthMm() * pxPerMm * FIT_SAFETY, ...)`。常量提取到 `labelImage.ts` 导出（`FIT_SAFETY_RATIO = 0.97`），打印 CSS 侧 import 同一常量——单一来源，杜绝两侧漂移。代价：触发缩号的行平均再小约 0.1mm，肉眼无感。

### D3：NO 行 700 → 600 双源同步

`.paper-* .label-code` 的 `font-weight: 700 → 600` 与 `LABEL_SPEC.fonts.code.weight: '700' → '600'` 同笔改（双源同参纪律）；600 字重文件随 D1 一并引入（ITEM 行 sans 600 不涉）。webfont 已消除主要差异，此为残余保险（浏览器私酿缩放/异常回退时 600 的跨字体离散更小）。

## Risks / Trade-offs

- [字体加载时序：webfont 异步加载晚于首次测量] → font-display: swap 下屏显首帧或回退系统字体，`fitLabelLines` 在字体就绪前测量可能少缩；用 `document.fonts.ready.then(fitLabelLines)` 补一次重测（打印前必然就绪），并在 renderQrCodes 路径保持现测量。
- [体积 +~100KB] → 拉丁子集三字重，仅 mono 文本使用；标签场景收益判定值得。
- [600 字重渲染略淡] → 热敏/激光打印对比度足够（V2 曾为可读性上调字号，600 在 3.4mm 下仍清晰）；如实测偏淡可回 700（webfont 已主防护）。

## Migration Plan

纯前端，随常规发版；无迁移无回滚风险。上线后**指定李雨霜电脑复打 100+ 编号标签验证**（本案回归判据），另抽 1~2 台未装开发字体的普通办公机验证。

## Open Questions

（无——三件套方向已在诊断沟通中与用户对齐；台州四项环境确认仍在途，但不影响本修复（不依赖触发点定位）。）
