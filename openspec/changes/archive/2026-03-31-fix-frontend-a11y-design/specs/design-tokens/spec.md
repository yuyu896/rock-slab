# 设计系统：设计令牌规范

设计令牌是设计系统的原子值，用于统一管理颜色、间距、排版等设计变量。

## ADDED Requirements

### Requirement: 状态颜色必须使用设计令牌

所有状态相关的颜色必须通过 CSS 变量定义，不得硬编码颜色值。

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

所有颜色令牌必须在深色模式下有对应的值。

#### Scenario: 深色模式颜色定义
- **WHEN** 定义新的设计令牌
- **THEN** 必须同时在 `:root` 和 `@media (prefers-color-scheme: dark)` 中定义
- **AND** 深色模式颜色应保持足够的对比度

#### Scenario: 状态色深色模式
- **WHEN** 系统切换到深色模式
- **THEN** 所有状态颜色自动使用深色变体
- **AND** 文本与背景对比度至少达到 4.5:1 (WCAG AA)

### Requirement: 常量文件引用 CSS 变量

TypeScript/JavaScript 中的状态颜色常量应当引用 CSS 变量，避免重复定义。

#### Scenario: 常量与 CSS 同步
- **WHEN** 在 `constants/index.ts` 中定义状态颜色
- **THEN** 应使用 `var(--color-status-xxx)` 格式
- **AND** 如果无法直接使用 CSS 变量，应从 `variables.css` 提取值保持同步

### Requirement: 建立 .impeccable.md 设计上下文文件

项目根目录必须包含 `.impeccable.md` 文件，记录设计上下文。

#### Scenario: 设计上下文文件
- **WHEN** 项目初始化
- **THEN** 根目录存在 `.impeccable.md` 文件
- **AND** 文件包含：目标用户、用例、品牌个性、设计方向

#### Scenario: 设计上下文内容
- **WHEN** 开发者进行设计相关工作
- **THEN** 应参考 `.impeccable.md` 中的品牌个性和设计方向
- **AND** 新的设计决策应与文档中定义的方向一致
