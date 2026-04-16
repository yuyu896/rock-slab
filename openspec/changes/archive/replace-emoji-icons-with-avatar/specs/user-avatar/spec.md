## ADDED Requirements

### Requirement: 文字头像渲染
系统 SHALL 在组织架构侧边栏人员节点中使用头像图标替代 emoji 表情。当用户未设置自定义头像时，系统 SHALL 显示姓名首字的文字头像（如"张三"显示"张"，"李四"显示"李"）。

#### Scenario: 显示姓名首字文字头像
- **WHEN** 用户未设置自定义头像（avatar 字段为空）
- **THEN** 系统在侧边栏节点和用户详情面板中显示姓名的第一个字符作为文字头像，使用角色对应的背景色

#### Scenario: 单字符姓名
- **WHEN** 用户姓名仅有一个字符（如"张"）
- **THEN** 系统显示该字符作为文字头像

### Requirement: 自定义头像显示
系统 SHALL 支持用户上传自定义头像图片。当用户已设置自定义头像时，系统 SHALL 优先显示自定义头像而非文字头像。

#### Scenario: 显示自定义头像
- **WHEN** 用户已上传自定义头像（avatar 字段有值）
- **THEN** 系统在侧边栏节点和用户详情面板中显示该用户自定义头像图片，以圆形裁切显示（CSS object-fit: cover）

#### Scenario: 自定义头像加载失败
- **WHEN** 用户自定义头像 URL 加载失败（如文件被删除）
- **THEN** 系统 SHALL 降级显示姓名首字文字头像

### Requirement: 头像上传
系统 SHALL 在功能栏左下角用户信息区域提供"更换头像"功能。点击头像 SHALL 触发文件选择器。

#### Scenario: 上传头像成功
- **WHEN** 用户点击功能栏左下角头像，选择一张 jpg/png/webp 格式且不超过 2MB 的图片并确认
- **THEN** 系统发送 `POST /api/users/<id>/avatar/` 上传图片，上传成功后刷新页面所有头像显示

#### Scenario: 上传文件格式不支持
- **WHEN** 用户选择了非 jpg/png/webp 格式的文件
- **THEN** 系统显示错误提示"仅支持 JPG、PNG、WebP 格式的图片"

#### Scenario: 上传文件过大
- **WHEN** 用户选择了超过 2MB 的文件
- **THEN** 系统显示错误提示"图片大小不能超过 2MB"

### Requirement: 头像上传 API
后端 SHALL 提供 `POST /api/users/<id>/avatar/` 端点，接收 multipart/form-data 格式的图片文件。

#### Scenario: 成功上传头像
- **WHEN** 客户端发送有效图片文件到 `POST /api/users/<id>/avatar/`
- **THEN** 系统保存图片到 `media/avatars/` 目录，更新用户的 avatar 字段，返回 200 和更新后的用户数据

#### Scenario: 上传非图片文件
- **WHEN** 客户端发送非图片文件
- **THEN** 系统返回 400 错误

#### Scenario: 非本人头像上传
- **WHEN** 普通用户尝试上传其他用户的头像
- **THEN** 系统返回 403 错误；管理员可以为任何用户上传头像

### Requirement: 移除 emoji 角色图标
系统 SHALL 在组织架构侧边栏人员节点中移除基于角色的 emoji 表情图标（`getRoleIcon` 函数），改用头像（自定义头像或文字头像）。

#### Scenario: 侧边栏节点不再显示 emoji
- **WHEN** 组织架构侧边栏渲染人员节点
- **THEN** 节点图标位置显示头像（自定义头像或姓名首字文字头像），不再显示 👑👔🎯📋💼 等 emoji

### Requirement: User 模型新增 avatar 字段
后端 User 模型 SHALL 新增可选的 `avatar` 字段，类型为 `ImageField`，上传路径为 `avatars/`。

#### Scenario: 用户 avatar 字段序列化
- **WHEN** 通过 API 获取用户数据
- **THEN** 返回数据中包含 `avatar` 字段，值为图片完整 URL 或 null
