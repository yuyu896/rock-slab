## Context

磐盘前端基于**纯 CSS + 自定义属性**构建设计系统（无 Tailwind / CSS-in-JS）。所有颜色令牌集中定义在 `frontend/src/styles/variables.css` 的 `:root`，并通过 `@media (prefers-color-scheme: dark)` 覆盖深色值；当前品牌主色为暖绿 oklch 色相 **145**。Element Plus 在 `main.ts` 全量引入默认样式（`element-plus/dist/index.css`），其组件主题色需通过覆盖 `--el-color-*` 系列令牌实现。`constants/index.ts` 中状态颜色以 `var(--color-*)` 形式引用 CSS 变量。约束（见现有 `design-tokens` spec）：状态色必须走令牌、必须支持深色模式、常量须引用 CSS 变量、根目录须存在 `.impeccable.md`。另：`Login.vue`、`Purchase.vue`、`Category.vue`、`Dashboard.vue`、`MobileScan.vue`、`styles/action-buttons.css`、`styles/variables.css` 共 7 处存在硬编码 `oklch(… 145)`。

## Goals / Non-Goals

**Goals:**
- 将全站品牌主色、背景、容器、侧边栏、文字、边框、阴影统一切换为白蓝。
- 品牌蓝覆盖 Element Plus 组件主题，组件与品牌一致。
- 全站统一白蓝主调：`success` 正向状态跟随品牌蓝；仅保留 `danger`(红) / `warning`(黄) 警示语义色，确保异常可读、不被品牌蓝淹没。
- 深色模式同步为蓝调，文本/背景对比度达 WCAG AA（≥4.5:1）。
- 消除前端所有硬编码绿色色相。

**Non-Goals:**
- 不重构样式架构（仍纯 CSS + 变量，不引入预处理器）。
- 不调整非颜色令牌（间距 / 字号 / 圆角 / 布局尺寸）。
- 不做运行时主题切换器；深色模式仍由 `prefers-color-scheme` 驱动。
- 不改 Element Plus 组件结构，仅覆盖令牌。
- 不涉及后端 / 部署配置。

## Decisions

### 决策 1：品牌主色采用蓝色色相 h≈250，沿用 oklch 与现有 50–900 梯度
**Why**：保持与 `variables.css` 相同的色彩空间（oklch）与梯度结构，改动面最小、感知均匀。h≈250 为专业蓝（介于标准蓝 240 与品牌蓝之间），L≈0.55 / c≈0.19（500 档）接近主流 B 端蓝（Ant Design `#1677ff`、Element `#409eff` 的 oklch 近似）。
**Alternatives**：改用 hex/hsl → 需重写全部梯度且失去感知均匀（否决）；h=240 → 偏冷（不取）。
**取值建议**：`--color-primary-500: oklch(0.55 0.19 250)`，50–900 按现有 L/c 比例平移（最终值在实施时定）。

### 决策 2：底色由"带绿调暖白"改为"中性白 / 极淡蓝调"
- `--color-bg-page: oklch(0.985 0.006 250)`、`--color-bg-card/elevated: oklch(0.998 0.003 250)`（近纯白、微蓝）。
- `--color-bg-sidebar: oklch(0.26 0.05 250)`（深绿 → 深蓝）。
- 文字 / 边框 / 阴影去除绿色色相，改为中性灰或带微蓝灰（色相统一到 250）。

### 决策 3：全站统一白蓝，仅保留警示语义色
- **全站主调统一白蓝**：品牌蓝用于交互 / 品牌元素（主按钮、链接、激活/选中态、品牌徽标、图表主系列、输入框聚焦），`success` 正向状态（资产在库、审批已通过、盘点匹配）**也跟随品牌蓝**，构成统一的白蓝视觉。
- **仅保留警示语义色**：`danger`（报废 / 驳回 / 缺失=红，色相 25）、`warning`（待审批=黄，色相 85）保留其色相，承担"一眼识别异常"的职能；`info` 复用品牌蓝。
**Why**：用户要求全站统一白蓝，故正向状态不再用绿色区隔；但 danger/warning 是功能性警示色，变蓝会丧失异常辨识度，故保留。
**Alternatives**：①正向状态保留绿（原方案）→ 违背"统一白蓝"诉求（否决）；②success/warning/danger 全部统一蓝 → 视觉最纯但牺牲警示辨识度，资产报废/审批驳回等异常无法一眼识别（否决）。

### 决策 4：Element Plus 主题通过 `global.css` 覆盖 `--el-color-*` 派生令牌
不使用 SCSS 主题定制（项目无 sass 预处理配置，改造成本高）。在 `styles/global.css` 的 `:root` 覆盖 `--el-color-primary` 及其 `light-3/5/7/8/9`、`--el-color-primary-dark-2`，映射到 `--color-primary-*`；并覆盖按钮 / switch / radio / checkbox / slider / tabs / tag / input focus 等关键组件涉及的派生变量。

### 决策 5：清理硬编码，统一令牌
7 处 `oklch(… 145)` 全部替换为对应 `--color-*` 变量引用（含图表主色，如 `Dashboard.vue` / `Reports.vue`）。

## Risks / Trade-offs

- **[品牌蓝与 info 蓝 / 链接蓝视觉同质]** → `info` 明确复用品牌蓝；链接沿用主色，不额外区分；交互态靠形状/字重而非色相差区分。
- **[正向状态跟随品牌蓝后，与交互元素同色]** → 在库/已通过/匹配标签改为品牌蓝浅底深字（`--color-primary-100`/`700`），与实心主按钮通过"浅底标签 vs 实心填充"的形态差异区分，不依赖颜色区隔。
- **[danger/warning 在蓝主题中显突兀]** → 接受并视为有益（警示即需醒目）；仅保留红/黄两色，限定用于真正的异常/待处理语义，不滥用为装饰色。
- **[Element Plus 派生令牌覆盖不全 → 部分组件残留默认色]** → 实施时遍历常用组件逐一目视验证；以"全站无绿色交互元素"为验收点。
- **[深色模式对比度不足]** → 用对比度工具抽验：主色文本于卡片背景、侧边栏白字、状态标签 text/bg 对比度 ≥ 4.5:1。
- **[图表 / 自定义 SVG 硬编码绿色]** → 在硬编码清理阶段一并排查 `Dashboard.vue`、`Reports.vue`、`MobileScan.vue` 等图表相关色值。
