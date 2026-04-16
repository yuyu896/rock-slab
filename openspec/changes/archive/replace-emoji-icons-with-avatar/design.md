## Context

组织架构侧边栏当前通过 `getRoleIcon(role)` 函数返回 emoji（admin→👑, manager→👔 等）作为人员节点图标，在模板的 `<span class="node-icon">` 中渲染。用户详情面板的 `profile-avatar` 使用姓名首字文字头像，但侧边栏未复用该逻辑。

后端 User 模型（`apps/users/models.py`）当前无 `avatar` 字段，使用 Django 默认的 `ImageField` 即可支持图片上传。前端使用 axios 发送请求，项目未引入图片裁剪库。

## Goals / Non-Goals

**Goals:**
- 移除 `getRoleIcon` 的 emoji 逻辑，侧边栏人员节点统一使用头像（自定义头像优先，降级为姓名首字文字头像）
- 后端 User 模型新增 `avatar` 可选字段，支持图片上传
- 前端功能栏左下角用户信息区域增加"更换头像"入口

**Non-Goals:**
- 不实现图片裁剪/压缩前端组件（直接上传原图）
- 不实现头像审核流程
- 不实现头像缓存策略（使用浏览器默认缓存）
- 不影响其他模块的头像显示逻辑

## Decisions

1. **后端使用 `ImageField` + Django media 存储**：User 模型新增 `avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)`，利用 Django 的 `DEFAULT_FILE_STORAGE`。无需引入第三方对象存储。

2. **前端降级策略**：优先渲染 `user.avatar` URL 作为 `<img>`；若 `avatar` 为空，渲染姓名首字文字头像（复用现有 `profile-avatar` 的 CSS 样式逻辑）。不在后端生成默认头像图片。

3. **头像上传 API**：新增 `POST /api/users/<id>/avatar/` 端点（而非 PUT 整个 user），使用 `multipart/form-data`，与其他用户编辑接口解耦。文件大小限制 2MB，仅允许 jpg/png/webp 格式。

4. **前端上传入口**：在 MainLayout 左下角用户信息区域的头像上增加点击事件，弹出文件选择 → 确认上传。上传成功后更新本地状态。

5. **移除 `getRoleIcon` 和 `getRoleStyle` 在侧边栏的使用**：`node-icon` 改为头像组件，`node-role` 标签保留角色文字标识但不再需要 `getRoleStyle` 提供的颜色样式（改用统一的角色标签样式）。注意：`getRoleStyle` 仍在用户详情面板和其他位置使用，不删除该函数。

## Risks / Trade-offs

- [头像存储占用磁盘空间] → 初期流量小，单张头像 < 2MB，可接受。后续可迁移至对象存储。
- [无图片裁剪可能导致显示不理想] → 使用 CSS `object-fit: cover` 统一裁切为圆形显示，前端无需裁剪组件。
- [上传大文件可能超时] → 前端限制 2MB，超时风险低。
