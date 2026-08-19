## 1. 后端：User 模型与 API

- [x] 1.1 User 模型新增 `system_avatar` 字段（CharField, max_length=20, null=True, blank=True），定义有效标识符常量列表 `SYSTEM_AVATAR_CHOICES = [f'geo-{i}' for i in range(1, 11)]`
- [x] 1.2 执行数据库迁移 `python manage.py makemigrations users` 和 `python manage.py migrate`
- [x] 1.3 UserViewSet 新增 `@action set_system_avatar`：POST /api/users/{id}/system-avatar/，接收 system_avatar 标识符，验证有效性，保存字段并同时清除 avatar 文件
- [x] 1.4 UserSerializer 新增 `system_avatar` 字段（read_only=False, required=False, allow_null=True）
- [x] 1.5 修改 `upload_avatar` action：上传自定义头像时自动清除 `system_avatar` 字段

## 2. 前端：预设头像组件

- [x] 2.1 创建 `frontend/src/components/SystemAvatars.vue` 组件：定义 10 个 SVG 几何头像（不同配色），接收 `modelValue`（当前选中标识符），emit `select` 事件
- [x] 2.2 头像网格布局：5列×2行，每个头像 48px 圆形，选中状态显示主题色边框，末尾放置"自定义上传"按钮（+图标）
- [x] 2.3 在 `frontend/src/api/users.ts` 新增 `setSystemAvatar(id, avatarKey)` API 函数

## 3. 前端：用户面板布局重构

- [x] 3.1 修改 `MainLayout.vue` 面板定位：从居中 Modal 改为侧边栏锚定 Popover（`.sidebar-footer` 添加 `position: relative`，面板使用 `position: absolute; left: calc(100% + 8px); bottom: 0`）
- [x] 3.2 重构面板内部结构为四个区域：顶部用户信息卡片（纯展示）、头像管理区（集成 SystemAvatars 组件）、信息编辑区、操作区
- [x] 3.3 面板视口溢出处理：JS 计算面板是否超出视口底部，超出时调整 `bottom` 为 `auto` 并设置 `top`；max-height: 80vh + overflow-y: auto
- [x] 3.4 头像显示优先级逻辑：在面板顶部卡片和侧边栏用户卡片中实现 avatar > system_avatar > 姓名首字母的渲染逻辑

## 4. 前端：组织架构页面头像适配

- [x] 4.1 在 `Organization.vue` 的 `getAvatarStyle()` 和头像渲染逻辑中集成预设头像 SVG 显示，支持 system_avatar 标识符到 SVG 的映射
- [x] 4.2 抽取头像渲染为共享工具函数 `frontend/src/utils/avatar.ts`（renderAvatar 函数，根据 avatar/system_avatar/initial 返回对应 VNode 或样式），供 MainLayout 和 Organization 共用

## 5. 测试与验证

- [x] 5.1 后端测试：验证 set_system_avatar API 的正常设置、无效标识符拒绝、与 avatar 的互斥清除
- [x] 5.2 前端手动验证：面板 Popover 定位正确、预设头像选择生效、自定义上传与预设互斥、组织架构页面预设头像渲染正确
