## 1. 定义白蓝核心令牌（variables.css）

- [x] 1.1 将 `--color-primary` 全梯度（50–900）色相由 145（绿）切换为蓝色（h≈250），500 档取 `oklch(0.55 0.19 250)`，其余按现有 L/c 比例平移
- [x] 1.2 将 `--color-bg-page`、`--color-bg-card`、`--color-bg-elevated` 改为中性白 / 极淡蓝调（色相 250 或无彩色，去绿色）
- [x] 1.3 将 `--color-bg-sidebar` 由深绿改为深蓝（如 `oklch(0.26 0.05 250)`）
- [x] 1.4 将 `--color-text-*`、`--color-border*`、`--shadow-*` 去除绿色色相，统一为中性灰或带微蓝灰（h≈250）

## 2. 正向状态色跟随品牌蓝（全站统一白蓝）

- [x] 2.1 将"正向状态"标签令牌（`--color-status-in-stock-*`、`--color-approval-approved-*`、`--color-inventory-matched-*`）的取值确认为引用 `--color-primary-*` 蓝色梯度（bg/text 成对、浅底深字），构成统一白蓝主调
- [x] 2.2 保持 `--color-warning`（黄/待审批）、`--color-danger`（红/报废·驳回·缺失）警示语义色相不变；`--color-info` 复用品牌蓝；`--color-success` 跟随品牌蓝
- [x] 2.3 确保正向状态标签（浅蓝底）与实心主按钮（蓝色填充）通过形态差异区分，不依赖颜色区隔

## 3. Element Plus 主题覆盖（global.css）

- [x] 3.1 在 `styles/global.css` 的 `:root` 覆盖 `--el-color-primary` 及派生令牌（`light-3/5/7/8/9`、`dark-2`），映射到 `--color-primary-*`
- [x] 3.2 覆盖常用组件涉及的主色派生变量（按钮 / switch / radio / checkbox / slider / tabs / tag / input focus 等），确保无残留默认色

## 4. 清理硬编码绿色（7 文件）

- [x] 4.1 `styles/variables.css`、`styles/action-buttons.css` 中的 `oklch(… 145)` 改为变量引用
- [x] 4.2 `views/Login.vue`、`views/Purchase.vue`、`views/Category.vue`、`views/Dashboard.vue`、`views/MobileScan.vue` 中的 `oklch(… 145)` 改为变量引用（含图表主色）；额外修复 `views/purchases/PurchaseDetail.vue` 已通过状态硬编码绿色 → 蓝色令牌
- [x] 4.3 全局检索确认无残留色相 145 的绿色硬编码（`oklch` / hex / rgb）；唯一保留：`utils/avatar.ts` geo-6 头像配色属装饰性多色头像盘（10 色之一），非品牌/状态色

## 5. 同步前端常量与设计上下文

- [x] 5.1 `constants/index.ts` 状态颜色常量已全部使用 `var(--color-*)` 令牌（无需改动，随令牌自动变蓝）
- [x] 5.2 更新 `.impeccable.md` 的品牌个性 / 设计方向描述为白蓝

## 6. 深色模式同步

- [x] 6.1 在 `@media (prefers-color-scheme: dark)` 中将主色、背景、侧边栏、文字/边框调整为蓝调深色
- [ ] 6.2 抽验深色模式对比度：主色文本于卡片背景、侧边栏白字、状态标签 text/bg 均 ≥ 4.5:1（WCAG AA）

## 7. 构建与回归验收

- [ ] 7.1 运行 `npm run build`（含类型检查）通过
- [ ] 7.2 目视回归：登录页、主布局侧边栏、资产/流转/盘点列表、移动端页面，主色与交互元素均为白蓝、无残留绿色
- [ ] 7.3 验证正向状态（在库/已通过/匹配）为蓝色、警示状态（报废/驳回/待审批/缺失）保留红黄，且均在浅/深色模式下可读
