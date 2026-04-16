# 实现任务

## 任务列表

- [x] **TASK-001**: 创建用户面板弹窗组件
  - 文件: `frontend/src/layouts/MainLayout.vue`
  - 新增弹窗容器（替代原有下拉菜单）
  - 弹窗布局：头部、头像区、信息区、操作区

- [x] **TASK-002**: 集成头像修改功能
  - 头像区域可点击
  - 支持图片选择、预览、上传
  - 复用现有 `uploadAvatar` 逻辑

- [x] **TASK-003**: 集成个人信息编辑
  - 姓名字段可直接编辑
  - 手机号、角色只读展示
  - 保存按钮调用 `updateUser` API

- [x] **TASK-004**: 集成修改密码功能
  - 点击「修改密码」切换到密码表单视图
  - 包含：旧密码、新密码、确认密码
  - 调用 `updatePassword` API

- [x] **TASK-005**: 集成退出登录
  - 保留确认对话框
  - 调用 `userStore.logout()`

- [x] **TASK-006**: 清理旧代码
  - 移除下拉菜单相关代码和样式
  - 移除 `/profile` 路由
  - 删除 `views/Profile.vue`

- [x] **TASK-007**: 测试验证
  - 构建通过 ✓
  - 弹窗交互已实现
  - 所有功能已集成

## 完成状态

✅ 所有任务已完成 (2026-04-07)

## 变更文件

- `frontend/src/layouts/MainLayout.vue` - 主要改动
  - 新增 `showUserPanel` 控制弹窗显示
  - 新增 `activeSection` 控制主面板/密码面板切换
  - 新增 `editForm`、`passwordForm` 响应式表单
  - 移除旧的下拉菜单逻辑和样式
  - 新增用户面板弹窗模板和样式

- `frontend/src/router/index.ts` - 路由清理
  - 移除 `/profile` 路由

- `frontend/src/views/Profile.vue` - 已删除
  - 不再需要独立的个人信息页面
