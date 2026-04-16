## Why

当前 PC 端用户面板弹窗存在排版问题：面板居中弹出而非锚定在侧边栏底部用户卡片附近，视觉割裂感强；头像区域、信息编辑区域和操作按钮纵向堆叠过于紧凑，缺乏呼吸感。头像方面目前仅支持本地上传，缺少系统预设头像供用户快速选择，用户体验不够友好。

## What Changes

- 重新设计 PC 端用户面板弹窗的布局结构，将弹窗锚定在侧边栏底部用户卡片旁侧弹出，而非页面居中
- 优化面板内部信息层级和间距，改善视觉节奏
- 新增系统预设头像功能：提供 8-10 个简约风格内置头像供用户选择
- 头像选择界面设计为"预设头像网格 + 自定义上传"双模式布局
- 后端新增头像选择字段（system_avatar），与自定义上传头像互斥

## Capabilities

### New Capabilities
- `user-panel-redesign`: PC 端用户面板弹窗的布局重构，包括面板定位方式、内部信息层级、间距和视觉节奏的优化
- `avatar-system`: 头像系统增强，包括预设头像资源管理、头像选择交互、预设/自定义双模式切换

### Modified Capabilities

## Impact

- 前端：`MainLayout.vue`（用户面板弹窗模板和样式大幅重构）、`api/users.ts`（新增系统头像选择 API 调用）、`types/index.ts`（User 类型新增 system_avatar 字段）
- 后端：`users/models.py`（User 模型新增 system_avatar 字段）、`users/views.py`（新增设置系统头像的 action）、`users/serializers.py`（序列化器新增字段）
- 静态资源：需要在项目中添加 8-10 个预设头像图片资源
- 数据库：User 表新增 system_avatar 字段（CharField，可为空）
