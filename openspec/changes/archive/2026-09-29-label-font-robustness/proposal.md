# 标签字体根治：自托管 webfont + 缩号安全余量（label-font-robustness）

## Why

2026-09-29 台州个案（仅李雨霜一台电脑）：编号过 100 的标签在打印预览缺末位数字，其他电脑正常。诊断锤实的代码侧脆弱点叠加：①标签等宽字体**未打包**（`--font-mono: JetBrains Mono → Fira Code → 系统等宽`），每台电脑解析结果可不同，打印与屏显的字体度量存在机器级差异；②打印通道缩号**贴线零余量**（塞下即停、步进 0.4px）+ `.fit` 行 `overflow:hidden`——打印度量宽一丝即裁末位；③NO 行 700 加粗，跨字体宽度差异最大。任何一台机器的打印度量偏差都会被放大成「缺一位」。

## What Changes

- **自托管 JetBrains Mono webfont**（拉丁子集，400/600/700 三字重，经 `@fontsource/jetbrains-mono` 引入或等价 vendor）：`@font-face` 随前端发布，全端（含打印/打印预览）渲染同一字体文件——字体环境差异归零，标签与全站 mono 场景一并受益。OFL 开源许可，自托管合规。
- **缩号安全余量 2~3%**：打印通道 `fitLabelLines` 目标宽改为 `clientWidth × 0.97`；导出通道 `fitLines` 调用侧同系数——两侧同口径，留出跨渲染引擎的度量抖动空间。
- **NO 行字重 700 → 600**：打印 CSS 与 `LABEL_SPEC.fonts.code.weight` 同步降为中粗（双源同参纪律），进一步压缩残余变宽幅度（webfont 兜底之下的第二道保险）。
- 测试：源码契约断言（@font-face 引入、余量系数、字重双源一致）+ 全量回归。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`：标签规范补充三条场景——等宽字体自托管全端一致、缩号安全余量、NO 行字重 600。

## Impact

- `frontend/package.json`（+@fontsource/jetbrains-mono 或 vendor woff2）、`styles/variables.css` 或入口样式（@font-face/导入）、`views/assets/AssetPrintDialog.vue`（fitLabelLines 余量、label-code 字重）、`utils/labelImage.ts`（fitLines 调用系数、LABEL_SPEC 字重）。
- 测试：`AssetPrintDialog.test.ts` / `labelImage.test.ts` 契约同步。
- 前端体积 +约 100KB（拉丁子集三字重 woff2，gzip 后更小）。不涉及后端。提案审查两问：无信息双存、无台账数量变动，通过。
