## Context

组织架构页面 `Organization.vue` 的角色标签存在两个显示问题：

1. **Emoji 图标问题**：`getRoleIcon` 函数为每个角色返回 emoji（👑👔🎯📋💼），在模板的人员详情区域以 `{{ getRoleIcon(role) }} {{ ROLE_LABELS[role] }}` 形式拼接显示。Emoji 在不同操作系统上渲染不一致，且在专业管理系统中不够正式。
2. **颜色对比度问题**：`getRoleStyle` 函数为不同角色返回 `{ bg, color }` 对象，当前 `admin`/`manager`/`supervisor` 三个角色的 `color` 值为 `white`，搭配的深色背景上对比度尚可，但在列表标签（`.node-role`）这种小尺寸场景中不够清晰。

当前角色样式映射：
```
admin:      { bg: 'oklch(0.20 0.04 250)', color: 'white' }
manager:    { bg: 'oklch(0.25 0.06 250)', color: 'white' }
supervisor: { bg: 'var(--color-primary-500)', color: 'white' }
leader:     { bg: 'var(--color-primary-100)', color: 'var(--color-primary-700)' }
staff:      { bg: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }
```

## Goals / Non-Goals

**Goals:**
- 移除角色标签中的 emoji 图标，保持纯文字显示
- 调整所有角色的文字颜色，确保在各使用场景（侧边栏树、人员详情、下属列表）中清晰可读

**Non-Goals:**
- 不修改角色体系或新增角色类型
- 不改动其他页面的角色显示逻辑

## Decisions

**1. 移除 `getRoleIcon` 函数及所有模板引用**

理由：该函数仅在 `Organization.vue` 的人员详情头部使用一次（`{{ getRoleIcon(selectedUser.role) }}`），移除后直接用 ROLE_LABELS 显示角色名即可，无需替代方案。

**2. 统一角色标签颜色为深色文字 + 浅色背景**

将所有角色的 `color` 从 `white` 改为深色系文字，背景改为浅色。这样在小尺寸标签和浅色背景页面中都有良好可读性。

新配色方案：
```
admin:      { bg: 'oklch(0.95 0.02 250)', color: 'oklch(0.25 0.05 250)' }
manager:    { bg: 'oklch(0.93 0.03 250)', color: 'oklch(0.30 0.06 250)' }
supervisor: { bg: 'var(--color-primary-100)', color: 'var(--color-primary-700)' }
leader:     保持不变
staff:      保持不变
```

理由：浅底深字方案在所有场景下对比度更稳定，与 leader/staff 的现有风格保持一致。

## Risks / Trade-offs

- **[视觉变化]** → 管理员/经理/主管角色的标签外观会从深底白字变为浅底深字，属于刻意优化
