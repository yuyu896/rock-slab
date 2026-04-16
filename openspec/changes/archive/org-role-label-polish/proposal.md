## Why

组织架构页面（Organization.vue）中存在两个 UI 显示问题：角色标签使用了 emoji 图标（如 👑👔🎯），在专业管理系统中显得不够正式；角色标签采用白色字体搭配深色背景，导致文字对比度不足、可读性差。

## What Changes

- 移除 `getRoleIcon` 函数及其在模板中的调用，角色标签仅显示文字名称（如"行政经理"）
- 调整 `getRoleStyle` 函数中各角色的背景色与字体色组合，确保文字清晰可读

## Capabilities

### New Capabilities

（无新增能力）

### Modified Capabilities

- `org-sidebar`: 移除侧边栏树节点中的 emoji 角色图标，优化角色标签文字颜色对比度

## Impact

- `frontend/src/views/Organization.vue`：`getRoleIcon` 函数删除、模板中引用移除、`getRoleStyle` 颜色值调整
