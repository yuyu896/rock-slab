## Context

当前组织树根是前端虚拟节点（`label` 硬编码「启航集团」，`add-group-root-visibility` 引入）。`filterEmployeesByNode` 的 `group` 分支返回全员（已实现）。用户要可编辑集团名，需把名字持久化到后端。

## Goals / Non-Goals

**Goals:**
- `Company` 单例模型存集团名，管理员可编辑，全局生效。
- 前端根节点显示 `Company.name`，可改名。

**Non-Goals:**
- 不做多集团（`Company` singleton，系统只一条记录）。
- 不扩展集团其他属性（本提案仅 `name`；未来可加 code/logo/地址等）。

## Decisions

### D1. Company 单例模型
**选择**：`organizations` 新建 `Company`（继承 `UUIDModel` + `TimestampedModel`），`name` 字段。系统**单例**（只一条记录）。迁移时 `get_or_create(name='启航集团')` seed。
**理由**：集团是组织顶层实体，`Company` 模型语义清晰；singleton 避免多集团复杂；未来可扩展属性（code/logo）。`get_or_create` 幂等，重复 seed 不报错。

### D2. API：GET 读 / PATCH 改名
**选择**：
- `GET /api/company/` → 返回 singleton（所有登录用户可读，供前端显示根名）
- `PATCH /api/company/` → 改 `name`（受 `manage_organizations`）

**理由**：读对所有人（前端要显示根名）；写限管理员。

### D3. 前端：根 label 用 Company.name + 编辑集团操作
**选择**：`Organization.vue` 的 `loadAll` 加载 `company`；`orgTree` 根节点 `label = company.name`（替代硬编码「启航集团」）；顶部栏集团根加「编辑集团」按钮 → 弹窗改 `name` → `updateCompany` → 刷新。
**理由**：根名来自后端，可编辑；编辑入口与「编辑区域」等一致。

## Risks / Trade-offs

- **[Company 表为空]** 迁移 seed `get_or_create` 保证有一条；前端 company 为空时降级显示默认名（如「集团」）。
- **[singleton 约束]** 应用层保证（取第一条 / 只 seed 一条），不强制 DB 唯一（避免迁移复杂）。

## Migration Plan

后端迁移（建 `Company` 表 + seed）+ 前端。`deploy.sh`（migrate 会 seed）。无数据丢失（新表）。

## Open Questions

- 编辑集团弹窗：仅 `name`，或加 `code`？倾向仅 `name`（最小，后续按需加）。
