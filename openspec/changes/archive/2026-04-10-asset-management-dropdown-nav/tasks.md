## 1. 状态管理与模板重构

- [x] 1.1 在 `MainLayout.vue` 中新增 `expandedMenu` ref（`ref<string | null>(null)`），用于追踪当前展开的下拉菜单 path
- [x] 1.2 新增 `toggleDropdown(path: string)` 方法：点击父菜单项时切换 `expandedMenu`，再次点击同一项则关闭
- [x] 1.3 新增 `closeDropdown()` 方法：关闭当前下拉
- [x] 1.4 新增 `isChildActive(item: NavItem)` 计算属性：判断当前路由是否匹配某父项的任一子路由，用于父项高亮
- [x] 1.5 修改模板中带 `children` 的菜单项渲染：将 `<template v-else>` 内的 `<ul class="nav-sublist">` 替换为浮层下拉组件结构

## 2. 下拉浮层组件实现

- [x] 2.1 创建下拉浮层 HTML 结构：`position: absolute` 容器，包含子菜单项列表，使用 `v-if="expandedMenu === item.path"` 控制显示
- [x] 2.2 为每个子菜单项绑定 `@click` 导航到对应路由，导航后调用 `closeDropdown()`
- [x] 2.3 子菜单项当前路由高亮：匹配 `route.path` 时添加 `active` class
- [x] 2.4 使用 Vue `<Transition>` 包裹下拉浮层，添加 fade/slide 过渡动画（200ms 内）

## 3. 点击外部关闭

- [x] 3.1 在 `onMounted` 中添加 `document.addEventListener('click', handleOutsideClick)` 监听器
- [x] 3.2 `handleOutsideClick` 检测点击目标是否在下拉浮层或触发按钮外，若是则调用 `closeDropdown()`
- [x] 3.3 在 `onUnmounted` 中移除事件监听器

## 4. 侧边栏折叠状态适配

- [x] 4.1 折叠状态下拉定位调整：`left: 100%`（紧贴图标右侧），固定宽度 160px
- [x] 4.2 展开状态下拉定位：锚定在菜单项右侧，宽度自适应
- [x] 4.3 折叠状态下父项图标仍可点击触发下拉（确保 `v-if="isCollapsed"` 时图标有点击处理）

## 5. 样式实现

- [x] 5.1 添加 `.nav-dropdown` 浮层基础样式：`position: absolute`、`z-index`、背景色、圆角、阴影
- [x] 5.2 添加 `.nav-dropdown-item` 子菜单项样式：hover 状态、active 高亮状态、间距
- [x] 5.3 添加下拉过渡动画 CSS（`.dropdown-enter-active` / `.dropdown-leave-active`）
- [x] 5.4 删除原有 `.nav-sublist` 和 `.nav-sublink` 相关 CSS（不再使用内联平铺）

## 6. 验证与清理

- [x] 6.1 验证展开侧边栏时：点击"资产管理"可正常弹出下拉，子项导航正确
- [x] 6.2 验证折叠侧边栏时：点击图标可弹出下拉，子项可导航
- [x] 6.3 验证点击外部区域关闭下拉
- [x] 6.4 验证当前路由为子路由时父项高亮
- [x] 6.5 确认移动端不受影响
