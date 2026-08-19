## Why

组织架构页面人员详情头部的布局存在两个对齐问题：角色标签与姓名未完全左对齐，编辑/删除按钮在头部区域靠顶部显示而非垂直居中。

## What Changes

- 将 `.detail-header` 的 `align-items` 从 `flex-start` 改为 `center`，使编辑/删除按钮垂直居中
- 确保 `.profile-info` 中角色标签与姓名文本左对齐

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `personnel-management`: 人员详情头部布局对齐优化

## Impact

- `frontend/src/views/Organization.vue`：`.detail-header` 和 `.profile-info` 相关 CSS 调整
