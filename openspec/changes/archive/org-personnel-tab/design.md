## Context

组织架构模块现有四个标签页：组织架构、区域管理、分公司管理、行政组。人员的新增/编辑/删除通过侧边栏树的弹窗操作。`personnel-management` 规格已完整定义了人员管理的需求（列表、搜索、筛选、CRUD），但前端未实现对应的标签页视图。

## Goals / Non-Goals

**Goals:**
- 新增"人员管理"标签页，以表格形式展示所有人员，支持搜索、筛选和 CRUD
- 复用现有的 `users` 数据、`fetchUsers`、`editItem('users')`、`deleteUserItem`、`toggleUserStatus` 等逻辑

**Non-Goals:**
- 不修改后端 API
- 不修改侧边栏的组织架构树

## Decisions

**1. 使用表格布局而非卡片**

人员数据是扁平结构，适合用表格展示（与分公司管理标签页一致）。复用 `.data-table` 样式。

**2. 搜索和筛选在前端本地过滤**

`users` 数据已在 `onMounted` 中全量加载，搜索和筛选在前端通过 computed 过滤实现，无需额外 API 调用。这与区域/分公司标签页的过滤方式一致。

**3. `activeTab` 类型扩展**

从 `'orgchart' | 'regions' | 'branches' | 'teams'` 扩展为 `'orgchart' | 'regions' | 'branches' | 'teams' | 'personnel'`。

## Risks / Trade-offs

- 前端全量过滤在大数据量时可能有性能问题 → 当前用户量级（<100）可接受，后续可改用 API 端筛选
