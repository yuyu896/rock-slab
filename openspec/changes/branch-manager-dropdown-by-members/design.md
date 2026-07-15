## Context

- 分公司编辑表单（`Organization.vue`）「负责人」`<select>` 现用 `users.filter(u => ['admin','director','manager','supervisor','leader'].includes(u.role))`——按角色(leader+)筛、不按分公司。
- `fetchUsers()` 以无参 `getUsers()` 拉取，`users` 含**全角色**员工及 `branch`(UUID) 字段（admin 数据范围=全部）。
- `editingItem.id` 为当前编辑分公司的 UUID；用户 `u.branch` 为其归属分公司 UUID。
- 「负责人」当前为必填（`<span class="required">*</span>` + 提交校验）。

## Goals / Non-Goals

**Goals:**
- 负责人下拉 = 该分公司归属员工（全角色，含 staff）。
- 新分公司可留空负责人（创建后再指派）。

**Non-Goals:**
- 不动「区域负责人」下拉。
- 不改后端用户接口/模型。
- 不改人员管理的归属逻辑。

## Decisions

### 决策 1：前端按分公司归属过滤、去角色限制
- **做法**：负责人 options 改为 `users.filter(u => u.branch === editingItem.id)`。
- **理由**：归属即成员、含 staff；数据已在 `users` 就绪，纯前端即可。

### 决策 2：负责人改可选
- **做法**：去掉「负责人」必填标记与提交校验。
- **理由**：新分公司尚无归属人员，必填会卡住创建；创建后到人员管理分配成员，再回来设负责人。

## Risks / Trade-offs

- **[新分公司负责人空]** 创建后需先分配成员再设负责人 → **缓解**：负责人可选，不阻塞创建；既有分公司从成员选，符合预期。

## Migration Plan

1. 前端：`Organization.vue` 负责人下拉过滤 + 可选。
2. 纯前端逻辑，**无 DB 迁移**；部署即生效。

## Open Questions

（暂无。）
