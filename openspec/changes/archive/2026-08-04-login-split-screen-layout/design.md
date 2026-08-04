## Context

磐盘是面向中国企业的固定资产管理系统，已上线 qhpanpan.top。当前**缺少专属品牌 logo**——PC 侧边栏顶部、浏览器 favicon、登录页都用一个通用立方体线条图标，品牌识别度弱；登录页是居中卡片式。本次既设计品牌 logo，又改造登录页布局。

设计系统已就绪（`styles/variables.css`）：白蓝配色、oklch 色板、完整设计令牌、支持 `prefers-color-scheme` 深色模式。品牌名为「磐盘」（行政资产盘点）。用户已选定 logo 概念为**资产层叠**（堆叠的盒 / 箱体轮廓）。

## Goals / Non-Goals

**Goals:**
- 设计磐盘专属品牌 logo（资产层叠概念），SVG 矢量，全站统一应用。
- 登录页改为左右分栏，左侧以 logo + 品牌标识为主，右侧登录表单。
- 响应式（窄屏单栏）+ 深色模式自适应。
- 复用设计令牌，不引入新依赖；登录逻辑零改动。

**Non-Goals:**
- 不改登录逻辑、后端、API、路由。
- 不引入位图图片资源（logo 用 SVG；favicon 提供 PNG 回退除外）。
- 不做吉祥物 / 复杂插画。
- 不做登录页之外的页面布局改造（仅替换各处 logo 图标）。

## Decisions

### D1. 布局：CSS Grid 左右两栏，断点 960px
**选择**：`.login-page` 用 `display: grid; grid-template-columns: 1fr 1fr`（或 `6fr 5fr`）；右侧表单 `align-items: center` 垂直居中。`@media (max-width: 960px)` 退化为 `grid-template-columns: 1fr`，隐藏左侧、表单全宽居中。
**理由**：Grid 直观表达两栏等高；960px 是桌面 / 平板常见分界。
**备选**：Flexbox——可行，但等高两栏 Grid 更简洁。

### D2. logo 概念：资产层叠（盒 / 箱堆叠）
**选择**：logo 主体为 2-3 层堆叠的资产盒 / 箱体轮廓（等距偏移、透视或轴测感），体现「固定资产的存储与管理」。几何扁平，线条 + 轻面性结合。最上层盒子可带一个**勾选记号**（隐喻「盘点完成」），把「资产」与「盘点」两个核心概念融合在一个图形里。
**理由**：直接呼应固定资产管理核心业务，场景识别度高；勾选点缀融入「盘点」语义。几何风格与系统现有线条图标协调。
**风格**：主色 `--color-primary-400/500/600`；勾选用 success 浅色变体。

### D3. logo 形态：SVG 组件 `BrandLogo.vue` + favicon 文件
**选择**：
- `components/BrandLogo.vue`：封装 logo 的内联 SVG，支持 props：`size`（尺寸）、`variant`（`'mono'` 单色用 currentColor / `'brand'` 品牌色渐变）、`hideText`（是否隐藏「磐盘」文字）。
- 静态 favicon：`public/favicon.svg`（主）+ `public/favicon.png`（老浏览器回退），`index.html` 引用。
**理由**：组件便于全站复用 + 主题变色（mono 版随 `currentColor`）；favicon 必须是独立静态文件（浏览器要求）。

### D4. logo 全站应用
**位置**：
- **favicon**：`index.html` 引用 `favicon.svg`（+ png 回退）。
- **PC 侧边栏顶部**（`layouts/MainLayout.vue`）：替换原通用立方体图标，用 `mono` 版（随侧边栏文字色）。
- **登录页左侧**：用 `brand` 版（品牌色渐变）作为主视觉。
**理由**：全站统一品牌；mono / brand 双版本适配不同背景（侧边栏深色用 mono，登录页用 brand 强调）。

### D5. 登录页左侧：logo 为主 + 标识 + 标语 + 轻量场景元素
**选择**：左侧视觉区 = 大号品牌色 logo（`brand` 版，偏上或居中）+ 「磐盘」标识 + 产品标语（「专业资产管理 · 高效盘点流程」）+ **轻量场景元素**（少量浮动小图标：资产盒 / 勾选 / 数据点，弱化复杂度，仅作氛围）。背景品牌蓝渐变 + 柔和光斑。
**理由**：logo 确立品牌主体；轻量元素补充业务氛围但不抢镜（区别于原方案的完整业务插画，避免与 logo 重复）。
**备选**：纯 logo + 标语（无场景元素）——更极简。倾向 logo + 轻量元素。

### D6. 右侧表单：垂直居中，max-width 420px
**选择**：右侧 `display: flex; flex-direction: column; justify-content: center`，表单 `max-width: 420px` 水平居中。保留现有表单结构（手机号 / 密码 / 显示密码 / 错误提示 / 登录按钮），可弱化卡片阴影以适配分栏。
**理由**：保留表单结构与交互，降低风险。

### D7. 深色模式 + 动效
**选择**：logo 与左侧背景用 `currentColor` + 设计令牌着色，深色模式自适应（左侧背景用 `primary-700/800`，logo 前景浅色）。可选克制微动效（浮动元素轻浮），用 `@media (prefers-reduced-motion: reduce)` 守护禁用。
**理由**：复用深色令牌零成本自适应；动效克制不分散登录注意力。

## Risks / Trade-offs

- **[favicon 强缓存]** → Mitigation：浏览器对 favicon 缓存激进，部署后用户可能仍见旧图标；可在 `index.html` 引用处加 `?v=2` 查询参数强制刷新，或提示用户硬刷新。
- **[logo 小尺寸可辨性]** → Mitigation：侧边栏 logo 显示在 ~32px，设计时测试该尺寸下勾选 / 堆叠细节是否清晰；过于复杂则简化（小尺寸用无勾选版）。
- **[全站替换遗漏]** → Mitigation：grep 旧立方体图标的 svg path，确认所有引用点替换；侧边栏 + 登录页 + favicon 三处是重点。
- **[登录逻辑误伤]** → Mitigation：只动 `<template>` / `<style>`，`<script setup>` 一行不改；实施后手动登录验证。

## Migration Plan

纯前端改造，无数据 / 后端迁移。步骤：
1. 新增 `BrandLogo.vue`（logo SVG，mono + brand 双版本）+ `public/favicon.svg/png`。
2. 重写 `Login.vue`（左右分栏 + 左侧 logo）+ 替换 `MainLayout.vue` 侧边栏图标 + 更新 `index.html` favicon。
3. `npm run build` + `npm run dev` 目测：登录页宽 / 窄屏 / 深色、侧边栏 logo、favicon。
4. 部署（前端 dist + favicon 由 nginx 服务，`deploy.sh` 或单独构建生效）。
- **回滚**：`git revert` 即可。

## Open Questions

1. **logo 是否含文字「磐盘」** **[已决策 2026-07-29]**：logo 图形本身为纯资产层叠图形（不含文字）；「磐盘」文字作为可分离文本，组件用 `hideText` 控制——favicon / 侧边栏用纯图形（`hideText`），登录页图形 + 文字。
2. **标语文案** **[已决策]**：默认「专业资产管理 · 高效盘点流程」。
3. **左侧轻量场景元素** **[已决策]**：保留轻量场景元素。
4. **favicon PNG 回退** **[已决策]**：SVG + PNG 双发。
