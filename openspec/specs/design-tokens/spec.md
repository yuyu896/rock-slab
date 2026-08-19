# 设计系统：设计令牌规范

## Purpose
设计系统：设计令牌规范。
## Requirements

设计令牌是设计系统的原子值，用于统一管理颜色、间距、排版等设计变量。

### Requirement: 状态颜色必须使用设计令牌

所有状态相关的颜色必须（SHALL）通过 CSS 变量定义，不得硬编码颜色值。

#### Scenario: 资产状态颜色
- **WHEN** 显示资产状态标签（在库/使用中/维修中/报废）
- **THEN** 必须使用 `--color-status-*` 系列变量
- **AND** 背景色和文本色必须成对使用

#### Scenario: 审批状态颜色
- **WHEN** 显示审批状态标签（待审批/已通过/已驳回）
- **THEN** 必须使用对应的审批状态令牌
- **AND** 颜色必须在浅色和深色模式下都保持可读性

#### Scenario: 库存状态颜色
- **WHEN** 显示库存充足/不足状态
- **THEN** 必须使用 `--color-success` 或 `--color-danger` 令牌
- **AND** 不得直接使用 `oklch()` 或其他颜色函数

### Requirement: 设计令牌必须支持深色模式

所有颜色令牌必须（SHALL）在深色模式下有对应的值。

#### Scenario: 深色模式颜色定义
- **WHEN** 定义新的设计令牌
- **THEN** 必须同时在 `:root` 和 `@media (prefers-color-scheme: dark)` 中定义
- **AND** 深色模式颜色应保持足够的对比度

#### Scenario: 状态色深色模式
- **WHEN** 系统切换到深色模式
- **THEN** 所有状态颜色自动使用深色变体
- **AND** 文本与背景对比度至少达到 4.5:1 (WCAG AA)

### Requirement: 常量文件引用 CSS 变量

TypeScript/JavaScript 中的状态颜色常量应当（SHALL）引用 CSS 变量，避免重复定义。

#### Scenario: 常量与 CSS 同步
- **WHEN** 在 `constants/index.ts` 中定义状态颜色
- **THEN** 应使用 `var(--color-status-xxx)` 格式
- **AND** 如果无法直接使用 CSS 变量，应从 `variables.css` 提取值保持同步

### Requirement: 建立 .impeccable.md 设计上下文文件

项目根目录必须（SHALL）包含 `.impeccable.md` 文件，记录设计上下文。

#### Scenario: 设计上下文文件
- **WHEN** 项目初始化
- **THEN** 根目录存在 `.impeccable.md` 文件
- **AND** 文件包含：目标用户、用例、品牌个性、设计方向

#### Scenario: 设计上下文内容
- **WHEN** 开发者进行设计相关工作
- **THEN** 应参考 `.impeccable.md` 中的品牌个性和设计方向
- **AND** 新的设计决策应与文档中定义的方向一致

### Requirement: 品牌主色必须为蓝色系

系统品牌主色（`--color-primary` 全梯度）MUST 采用蓝色色相，并保持 50–900 完整梯度，用于交互与品牌元素；MUST NOT 保留绿色色相。

#### Scenario: 品牌主色为蓝色

- **WHEN** 读取 `:root` 中的 `--color-primary` 与 `--color-primary-500`
- **THEN** 其 oklch 色相 MUST 位于蓝色区间（约 240–255）
- **AND** MUST NOT 为绿色色相 145

#### Scenario: 品牌色用于交互元素

- **WHEN** 渲染主按钮、激活态导航、选中项、品牌徽标、图表主系列
- **THEN** MUST 使用 `--color-primary-*` 系列令牌
- **AND** MUST NOT 使用硬编码颜色字面量

### Requirement: 背景与容器必须为白色或中性色

页面与容器底色 MUST 为中性白或极淡蓝调，MUST NOT 带绿色色相；侧边栏 MUST 为深蓝。

#### Scenario: 页面背景为中性白

- **WHEN** 渲染 `--color-bg-page`、`--color-bg-card`、`--color-bg-elevated`
- **THEN** 其色相 MUST NOT 为绿色（145）
- **AND** MUST 为中性或蓝色调（约 240–255 或无彩色）

#### Scenario: 侧边栏为深蓝

- **WHEN** 渲染主布局侧边栏
- **THEN** `--color-bg-sidebar` MUST 为蓝色色相的深色
- **AND** MUST NOT 为深绿

### Requirement: 全站统一白蓝，仅保留警示语义色

全站配色 MUST 统一为白蓝：品牌蓝承载交互 / 品牌语义，`success` 正向状态 MUST 跟随品牌蓝；仅 `danger` / `warning` 保留警示语义色相。

#### Scenario: 正向状态跟随品牌蓝

- **WHEN** 显示资产"在库"、审批"已通过"、盘点"匹配"等正向状态标签
- **THEN** MUST 使用品牌蓝 `--color-primary-*` 系列令牌（bg/text 成对，浅底深字）
- **AND** MUST NOT 使用绿色（色相 145）

#### Scenario: 警示语义色保留红黄

- **WHEN** 显示报废 / 驳回 / 缺失等危险状态，或待审批等警告状态
- **THEN** `--color-danger` MUST 为红、`--color-warning` MUST 为黄
- **AND** 警示语义色相 MUST NOT 随品牌色变蓝，确保异常状态一眼可辨

### Requirement: 禁止硬编码品牌色与绿色色相

样式与组件中 MUST NOT 直接书写 `oklch()`/hex 等颜色字面量来表示品牌色或绿色色相；MUST 通过设计令牌引用。

#### Scenario: 源码无绿色色相硬编码

- **WHEN** 检索前端源码中的颜色字面量
- **THEN** MUST NOT 存在色相为 145 的绿色硬编码（oklch 或等价值）
- **AND** 新增颜色 MUST 使用 `--color-*` 变量

#### Scenario: Element Plus 主题与品牌同步

- **WHEN** 渲染 Element Plus 组件（按钮 / 开关 / 单选 / 复选 / 输入框聚焦 / 标签页 / 标签等）
- **THEN** 其主色 MUST 通过 `--el-color-primary` 派生令牌映射到 `--color-primary-*`
- **AND** MUST NOT 显示绿色或 Element 默认蓝以外的残留品牌绿

### Requirement: 深色模式品牌配色同步为蓝调

深色模式下品牌主色、背景、侧边栏 MUST 同步为蓝调，且文本与背景对比度 MUST 达 WCAG AA（≥4.5:1）。

#### Scenario: 深色模式使用蓝色主色

- **WHEN** 系统处于 `prefers-color-scheme: dark`
- **THEN** `--color-primary`、`--color-bg-*`、`--color-bg-sidebar` MUST 为蓝色调
- **AND** 主色文本于卡片背景、侧边栏白字的对比度 MUST ≥ 4.5:1

