## Why

当前系统整体采用**暖绿色**品牌配色（oklch 色相 145，集中定义在 `styles/variables.css`）。但磐盘是企业级固定资产管理系统，白蓝配色更能传达**专业、可信、科技感**，也更贴近主流 B 端管理后台的视觉习惯与用户预期。现需将整体品牌色调从暖绿切换为白蓝，统一全站视觉风格。

## What Changes

- **品牌主色系由绿色改为蓝色**：`--color-primary` 全梯度（50–900）从 oklch 色相 145（绿）切换为蓝色色相（约 240–255），覆盖按钮、链接、激活态、徽标、图表主色等。
- **背景与容器色调由"带绿调暖白"改为"中性白/极淡蓝调"**：`--color-bg-page`、`--color-bg-card`、`--color-bg-elevated` 去除绿色色相；侧边栏 `--color-bg-sidebar` 由深绿改为深蓝。
- **文字 / 边框 / 阴影色**去除绿色色相，改为中性灰 / 带微蓝灰，与新主色协调。
- **全站统一白蓝，仅保留警示语义色**：`success` 正向状态（资产在库、审批已通过、盘点匹配）跟随品牌蓝，构成统一的白蓝主调；仅保留 `danger`（报废/驳回/缺失=红）、`warning`（待审批=黄）作为警示语义色，确保异常状态一眼可辨；`info` 复用品牌蓝。
- **同步 Element Plus 主题**：覆盖 `--el-color-primary` 系列令牌，使按钮、开关、选择器等组件与品牌蓝一致。
- **同步前端常量**：`constants/index.ts` 中状态颜色常量与新令牌保持一致。
- **清理硬编码绿色**：替换 7 个文件中直接书写的 `oklch(… 145)`（`Login.vue`、`Purchase.vue`、`Category.vue`、`Dashboard.vue`、`MobileScan.vue`、`styles/action-buttons.css`、`styles/variables.css`）为变量引用。
- **深色模式同步**：深色模式下的主色、背景、侧边栏一并调整为蓝调，保持对比度达标（WCAG AA）。

## Capabilities

### New Capabilities
<!-- 无新增能力，本变更是对现有设计令牌规范的修改 -->

### Modified Capabilities
- `design-tokens`: 品牌主色与背景/容器色调的定义从暖绿改为白蓝，全站统一白蓝配色（`success` 正向状态跟随品牌蓝）；仅保留 `danger`/`warning` 警示语义色；新增品牌配色方向约束（主色=蓝、底色=白）；深色模式同步调整为蓝调。

## Impact

- **前端样式（核心）**：`frontend/src/styles/variables.css`（令牌重定义）、`styles/global.css`、`styles/action-buttons.css`（Element Plus 与按钮主题覆盖）。
- **硬编码替换（7 文件）**：`views/Login.vue`、`views/Purchase.vue`、`views/Category.vue`、`views/Dashboard.vue`、`views/MobileScan.vue` 及上述两个样式文件中的 `oklch(145)`。
- **常量同步**：`frontend/src/constants/index.ts` 状态颜色常量。
- **设计上下文**：`.impeccable.md` 中的品牌个性 / 设计方向描述需同步为白蓝。
- **回归验收**：登录页、主布局侧边栏、各列表页（资产/流转/盘点）、移动端页面、深色模式下主色、按钮、激活态、状态标签、图表主色均为白蓝且无残留绿色；正向状态（在库/已通过/匹配）为蓝，警示状态（报废/驳回/待审批/缺失）保留红黄且在浅/深色模式下可读。
- **后端 / 运维**：无接口契约变更，无部署配置变更（纯前端样式）。
