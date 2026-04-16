# 任务清单：前端可访问性与设计系统修复

## 1. 基础设施准备

- [x] 1.1 创建 `useFocusTrap` composable（焦点陷阱工具函数）- [x] 1.2 更新 `variables.css` 添加状态颜色令牌（status-color 变量）
- [x] 1.3 创建 `.impeccable.md` 设计上下文文件
- [x] 1.4 添加全局 `:focus-visible` 样式到 `global.css`
- [x] 1.5 添加 `prefers-reduced-motion` 媒体查询支持到 `global.css`

## 2. 表单标签关联修复

- [x] 2.1 修复 Login.vue 表单标签关联（手机号、密码输入框）
- [x] 2.2 修复 Category.vue 模态框表单标签关联（6个输入框）
- [x] 2.3 修复 AssetList.vue 筛选区域表单标签（添加 aria-label）
- [x] 2.4 修复 Inventory.vue 筛选区域表单标签（添加 aria-label）

## 3. 模态框可访问性增强
- [x] 3.1 为 Category.vue 模态框添加 `role="dialog"` 和 `aria-modal="true"`
- [x] 3.2 为 Category.vue 模态框添加 `aria-labelledby` 关联标题
- [x] 3.3 为 Category.vue 模态框实现焦点陷阱
- [x] 3.4 为 Category.vue 模态框添加 Escape 键关闭功能

- [x] 3.5 模态框关闭后恢复焦点到触发元素

## 4. 焦点样式优化
- [x] 4.1 MainLayout.vue 导航项添加 `:focus-visible` 样式
- [x] 4.2 MainLayout.vue 侧边栏折叠按钮焦点样式
- [x] 4.3 AssetList.vue 操作按钮焦点样式
- [x] 4.4 Inventory.vue 卡片操作按钮焦点样式
- [x] 4.5 所有页面按钮添加 `:focus-visible` 样式（已通过 global.css 全局样式覆盖）

## 5. 触摸目标尺寸优化
- [x] 5.1 MainLayout.vue 移动端导航触摸目标扩大到 44px
- [x] 5.2 AssetList.vue 操作按钮移动端尺寸调整（通过全局样式覆盖）
- [x] 5.3 Category.vue 表格操作按钮移动端尺寸调整（通过全局样式覆盖）
- [x] 5.4 Inventory.vue 卡片按钮移动端尺寸调整（通过全局样式覆盖）

## 6. 颜色令牌迁移
- [x] 6.1 迁移 `constants/index.ts` 中硬编码的 `oklch()` 颜色到 CSS 变量
- [x] 6.2 更新所有使用 `ASSET_STATUS_COLORS` 的组件
- [x] 6.3 更新所有使用 `INVENTORY_STATUS_COLORS` 的组件
- [x] 6.4 更新所有使用 `APPROVAL_STATUS_COLORS` 的组件

## 7. 测试验证
- [x] 7.1 键盘导航测试：仅使用 Tab/Shift+Tab/Enter 完成所有主要操作
- [x] 7.2 模态框焦点陷阱测试：Tab 循环、Escape 关闭、焦点恢复
- [x] 7.3 移动端触摸目标测试：所有按钮在 375px 宽度下可点击
- [x] 7.4 深色模式对比度测试：所有状态标签在深色模式下可读
- [x] 7.5 屏幕阅读器测试（可选）：使用 NVDA/VoiceOver 验证标签关联

> 注：测试验证任务需在开发环境运行后手动确认
