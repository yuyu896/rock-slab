# 实现任务

## 任务列表

- [x] **TASK-001**: 重构用户信息区域交互
  - 文件: `frontend/src/layouts/MainLayout.vue`
  - 新增下拉菜单组件
  - 移除独立的退出按钮
  - 点击用户区域展开菜单
  - 菜单项：修改头像、修改个人信息、退出登录

- [x] **TASK-002**: 实现头像修改对话框
  - 文件: `frontend/src/layouts/MainLayout.vue`
  - 支持图片预览和上传
  - 复用现有 `uploadAvatar` 逻辑

- [x] **TASK-003**: 优化侧边栏文字对比度
  - 文件: `frontend/src/layouts/MainLayout.vue`
  - 提升文字对比度至 WCAG AA 标准
  - `.nav-link` 颜色改为 `rgba(0, 0, 0, 0.75)`
  - `.nav-sublink` 颜色改为 `rgba(0, 0, 0, 0.6)`
  - `.user-name` 颜色改为 `rgba(0, 0, 0, 0.85)`
  - `.user-role` 颜色改为 `rgba(0, 0, 0, 0.55)`

- [x] **TASK-004**: 调整菜单顺序
  - 文件: `frontend/src/layouts/MainLayout.vue`
  - 修改 `navItems` 数组顺序
  - 「统计报表」移动到「工作台」下方

- [x] **TASK-005**: 测试验证
  - 构建通过 ✓
  - 下拉菜单交互已实现
  - 头像上传对话框已实现
  - 退出登录带确认对话框
  - 文字对比度已优化
  - 菜单顺序已调整

## 完成状态

✅ 所有任务已完成 (2026-04-03)

## 变更文件

- `frontend/src/layouts/MainLayout.vue` - 主要改动文件
  - 新增 `showUserMenu` 控制下拉菜单显示
  - 新增 `showAvatarDialog`、`selectedFile`、`previewUrl` 用于头像上传
  - 重构用户信息区域模板，使用下拉菜单
  - 新增头像上传对话框
  - 优化文字对比度
  - 调整菜单顺序
