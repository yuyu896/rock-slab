## Context

当前 `MainLayout.vue` 侧边栏中，"资产管理"菜单项包含 3 个子项（资产列表、采购入库、调拨记录），通过 `<ul class="nav-sublist">` 以内联平铺方式展开在侧边栏内部。这种平铺方式占用了较多垂直空间，且当子菜单数量增长时会导致侧边栏过长。

技术栈：Vue 3 + TypeScript + Element Plus，CSS 自定义属性体系。

## Goals / Non-Goals

**Goals:**
- 将"资产管理"子菜单从内联平铺改为浮层下拉列表，节省侧边栏垂直空间
- 下拉列表锚定在"资产管理"菜单项旁侧，不占据侧边栏固有空间
- 点击下拉项直接导航，点击外部区域或再次点击父项关闭下拉
- 侧边栏折叠状态下，通过悬浮或点击图标也能展开下拉
- 动画过渡自然（展开/收起）

**Non-Goals:**
- 不修改路由结构，`/assets/list`、`/assets/purchase`、`/assets/transfer` 保持不变
- 不影响其他菜单项的行为
- 不涉及后端改动
- 不修改移动端 MobileLayout

## Decisions

### 1. 下拉实现方式：纯 CSS + 少量 JS 状态管理

**选择**：使用 `position: absolute` 浮层 + Vue ref 控制显示/隐藏状态
**理由**：
- 与项目当前侧边栏实现风格一致（无额外 UI 库依赖）
- 代码量最少，改动范围可控
- 已有用户面板的绝对定位经验可复用

**备选**：Element Plus `el-dropdown` / `el-popover` — 引入额外组件依赖，样式定制受限。

实现方式：
- 新增 `expandedMenu` ref，存储当前展开的菜单 path（如 `'/assets'`）
- 点击"资产管理"时切换 `expandedMenu`，而非展开内联列表
- 下拉浮层使用 `position: absolute; left: 100%; top: 0` 定位在菜单项右侧
- 侧边栏折叠时，下拉定位调整为对齐图标中心

### 2. 点击外部关闭：document click listener

**选择**：在 `onMounted` 中注册 `document.addEventListener('click', ...)` 检测外部点击
**理由**：简单可靠，项目已有类似模式（用户面板遮罩层）

### 3. 侧边栏折叠状态适配

**选择**：折叠时下拉浮层仍可用，定位改为紧贴图标右侧，宽度固定 160px
**理由**：折叠后侧边栏宽度仅 64px，下拉需要完整展示文字标签

### 4. 当前路由高亮

父级菜单项在子路由激活时（如当前在 `/assets/list`）显示高亮样式，下拉中对应子项也高亮。

## Risks / Trade-offs

- **浮层遮挡风险**：下拉可能被主内容区遮挡 → 设置 `z-index` 高于主内容区
- **触摸设备兼容**：纯 hover 在触摸设备不可用 → 折叠状态下用 click 触发而非 hover
- **下拉定位溢出**：视口底部可能溢出 → 下拉高度有限（3项），风险极低
