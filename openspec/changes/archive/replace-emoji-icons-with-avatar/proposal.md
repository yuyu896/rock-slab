## Why

组织架构侧边栏当前使用角色对应的 emoji 表情包（👑👔🎯📋💼）作为人员图标，不够专业且无法区分同角色的不同人员。需要改为姓名首字文字头像（如"张三"→"张"），并支持用户上传自定义头像，使人员标识更加直观和个性化。

## What Changes

- 移除侧边栏人员节点的 emoji 角色图标（`getRoleIcon` 函数），改用姓名首字文字头像
- 后端 User 模型新增 `avatar` 字段（图片上传，可选）
- 后端新增头像上传 API 端点（`POST /api/users/<id>/avatar/`）
- 前端侧边栏节点：优先显示自定义头像，未设置时降级为姓名首字文字头像
- 前端用户详情面板：同步显示头像
- 前端功能栏左下角用户信息区域：增加更换头像入口

## Capabilities

### New Capabilities
- `user-avatar`: 用户头像管理功能，包含文字头像渲染、自定义头像上传、头像展示

### Modified Capabilities

## Impact

- 后端：`apps/users/models.py` 新增 `avatar` 字段；`apps/users/serializers.py` 新增 avatar 序列化；`apps/users/views.py` 新增头像上传端点；需配置 media 存储和 URL
- 前端：`Organization.vue` 侧边栏节点渲染、用户详情面板；`MainLayout.vue` 左下角用户信息区域；新增头像上传组件或逻辑；`api/users.ts` 新增上传接口
- 依赖：Django media 文件配置、前端图片裁剪/压缩（可选）
