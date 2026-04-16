# 修复前端可访问性与设计系统问题

## Why

前端设计审计发现可访问性得分仅为 2/4，存在 WCAG AA 合规风险。主要问题包括：表单缺少标签关联、交互元素缺少键盘焦点样式、模态框缺少 ARIA 属性。同时发现响应式设计和主题系统存在硬编码颜色等问题。这些缺陷会影响残障用户和键盘用户的正常使用，需要在发布前修复。

## What Changes

### 可访问性修复
- 为所有表单输入添加关联的 `<label>` 元素（`for` 属性）
- 为交互元素添加 `:focus-visible` 焦点样式
- 为模态框添加 `role="dialog"`, `aria-modal="true"`, `aria-labelledby` 属性
- 实现模态框焦点陷阱 (focus trap)
- 添加 `prefers-reduced-motion` 媒体查询支持

### 响应式设计优化
- 增大移动端触摸目标尺寸至 44x44px 最小值
- 为水平滚动表格添加滚动指示器
- 优化移动端布局断点

### 主题系统强化
- 将硬编码的 `oklch()` 颜色值迁移到 CSS 变量
- 确保深色模式下状态颜色一致性
- 创建 `.impeccable.md` 设计上下文文件

## Capabilities

### New Capabilities

- `a11y-form-labels`: 表单输入与标签关联规范，确保所有输入框有关联的 label 元素
- `a11y-focus-management`: 键盘焦点样式和焦点陷阱规范，支持键盘导航用户
- `a11y-aria-attributes`: ARIA 属性使用规范，为交互组件添加适当的语义
- `responsive-touch-targets`: 移动端触摸目标尺寸规范，符合 44px 最小值要求
- `design-tokens`: 设计令牌系统规范，统一管理颜色、间距等设计变量

### Modified Capabilities

无需修改现有规格，此次为新增能力。

## Impact

### 受影响文件
- `frontend/src/views/Login.vue` - 表单标签关联
- `frontend/src/views/Category.vue` - 模态框 ARIA、表单标签
- `frontend/src/views/AssetList.vue` - 焦点样式、触摸目标
- `frontend/src/views/Inventory.vue` - 焦点样式、触摸目标
- `frontend/src/layouts/MainLayout.vue` - 导航焦点样式
- `frontend/src/styles/variables.css` - 新增设计令牌
- `frontend/src/constants/index.ts` - 迁移硬编码颜色

### 受影响系统
- 所有表单组件
- 所有模态框/弹窗
- 所有交互按钮和链接

### 依赖
- 无新增外部依赖
- 使用原生 CSS `:focus-visible` 和媒体查询

### 风险
- **低风险**: 主要是添加属性和样式，不改变功能逻辑
- 需要回归测试确保模态框焦点陷阱不影响现有交互
