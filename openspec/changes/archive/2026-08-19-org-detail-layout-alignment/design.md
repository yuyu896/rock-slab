## Context

组织架构页面 `Organization.vue` 的人员详情头部（`.detail-header`）采用 flex 布局，左侧是头像+姓名+角色的组合（`.user-profile`），右侧是编辑/删除按钮（`.detail-actions`）。

当前 CSS：
- `.detail-header` 设置了 `align-items: flex-start`，导致右侧按钮组贴顶部
- `.profile-info` 中姓名（h2）和角色标签（span）在 flex column 中，角色标签带 padding 和 `width: fit-content`

## Goals / Non-Goals

**Goals:**
- 编辑/删除按钮在详情头部垂直居中
- 角色标签与姓名文本左对齐

**Non-Goals:**
- 不修改头像、按钮的功能逻辑
- 不影响行政组详情头部的布局（已居中的无需改动）

## Decisions

**1. `.detail-header` 改为 `align-items: center`**

将 `align-items: flex-start` 改为 `align-items: center`，使按钮组与左侧内容垂直居中对齐。

**2. `.profile-info` 添加 `align-items: flex-start`**

显式设置 `align-items: flex-start`，确保角色标签与姓名左对齐。

**3. `.profile-role` 移除左侧 padding**

当前 `.profile-role` 有 `padding: 4px 10px`，10px 的左内边距导致角色文字比姓名文字偏右 10px。改为 `padding: 2px 0`，移除水平内边距，仅保留微小的垂直间距，使角色文字与姓名文字精确左对齐。同时移除 `border-radius`，因为无内边距后圆角背景没有意义。

## Risks / Trade-offs

- 按钮居中后，在姓名较长换行时按钮仍会相对整个头部居中而非跟随文字位置，属于可接受的折中
- 移除角色标签的 padding 后，背景色会紧贴文字边缘，视觉上从"徽章"变为"高亮文字"风格
