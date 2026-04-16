## 1. 后端模型与序列化器

- [x] 1.1 User 模型新增 `avatar = ImageField(upload_to='avatars/', null=True, blank=True)` 字段
- [x] 1.2 执行数据库迁移 `python manage.py makemigrations users` 和 `python manage.py migrate`
- [x] 1.3 UserSerializer 的 fields 列表新增 `avatar` 字段
- [x] 1.4 settings 配置 MEDIA_URL 和 MEDIA_ROOT，urls.py 添加 media URL 路由

## 2. 后端头像上传 API

- [x] 2.1 新增 `POST /api/users/<id>/avatar/` 端点，接收 multipart/form-data，验证文件类型（jpg/png/webp）和大小（≤2MB）
- [x] 2.2 权限控制：仅本人或管理员可上传，其他人返回 403
- [x] 2.3 注册新 URL 路由到 users app 的 urls.py

## 3. 前端 API 与类型

- [x] 3.1 前端 User 类型新增 `avatar?: string` 字段
- [x] 3.2 `api/users.ts` 新增 `uploadAvatar(id: string, file: File)` 函数，发送 multipart/form-data

## 4. 前端侧边栏头像渲染

- [x] 4.1 移除 `getRoleIcon` 函数在侧边栏模板中的使用（`.node-icon` 节点）
- [x] 4.2 新增 `getAvatarUrl(user)` 和 `getInitial(name)` 辅助函数
- [x] 4.3 侧边栏节点模板：`node-icon` 改为条件渲染——有 avatar 显示 `<img>`，否则显示姓名首字文字圆圈
- [x] 4.4 添加文字头像和图片头像的 CSS 样式（圆形裁切、object-fit: cover、角色背景色）

## 5. 前端用户详情面板

- [x] 5.1 用户详情 `profile-avatar` 区域：优先显示自定义头像 `<img>`，降级为现有姓名首字文字头像
- [x] 5.2 下属列表中的 `sub-avatar` 同步使用头像渲染逻辑

## 6. 前端头像上传功能

- [x] 6.1 MainLayout.vue 左下角用户信息区域：头像增加点击事件，触发文件选择
- [x] 6.2 文件选择后验证格式和大小，调用 `uploadAvatar` API
- [x] 6.3 上传成功后刷新 userStore 数据，页面所有头像自动更新

## 7. 验证

- [x] 7.1 确认未上传头像时所有位置正确显示姓名首字文字头像
- [x] 7.2 确认上传头像后侧边栏、详情面板、功能栏左下角同步显示自定义头像
- [x] 7.3 确认删除头像后降级回文字头像
