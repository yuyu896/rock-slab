## Context

`UserViewSet` 写路径现有两道闸：① `required_operations`（update/destroy 需 `manage_users`）② `_validate_in_scope`（数据范围：admin/本人豁免 → scope.all 无条件放行 → 否则限授权分公司内）。两道闸都不比较**目标用户**的岗位等级——`MANAGEABLE_ROLES` 权线表只用于「请求带 role 字段」时的分配校验（`_validate_role_assignment`）。动态复现已证明：manager + manage_users + scope.all 可改/删 admin；同分公司内 manager 可改 director；manager 可把 director 降级为 leader。

## Goals / Non-Goals

**Goals:**

- 越权写（改/删高岗位用户）与降级攻击在同一点封堵，返回 400 且不落库
- 管理语义与分配语义一致：**能分配什么岗位，才能管理什么岗位的用户**
- admin 与本人操作不受影响；同岗互管（manager↔manager）保持既有设计

**Non-Goals:**

- 不改 list/retrieve 的通讯录只读口径（属另一议题）
- 不修 audit 装饰器对 400 误记成功的缺陷（另案）
- 不动 `MANAGEABLE_ROLES` 表本身、不引入数值角色等级、不改前端

## Decisions

**1. 复用 `MANAGEABLE_ROLES` 作唯一权线依据，而非新造等级数值比较。**
数值比较（L1>L2>…，禁止操作不高于自身的目标）会顺带禁止 manager 同岗互管——与既有「分公司行政互建账号」的刻意设计冲突（views.py:17-19 注释）。`MANAGEABLE_ROLES` 已按岗位编码了组织意图（admin 全量、director 管 manager/leader、manager 管 manager/leader、leader 仅本人），复用它让「分配权线」与「管理权线」天然同一，无双份事实。代价：director 无法互管 director（须 admin 介入），与分配权线现状一致，非新增限制。

**1a. 退役岗位按换岗目标归一化计权线。**
`supervisor`/`staff` 不在 `MANAGEABLE_ROLES` 表内，直接查表会把存量「supervisor/staff 用户被 manager 编辑」的过渡行为拦断（既有绿灯用例与 position-appointment-permissions 的「存量按既有授权正常工作」要求）。按 `migrate_positions` 的换岗映射把两者在权线口径上视为 `manager`（操作者与目标两侧同样归一）：存量管理关系不冻结，而对在职高岗位（admin/director）的越权照样拦。

**2. 校验放在 `_validate_in_scope` 内、scope 解析之前，基于目标用户当前岗位。**

```
admin → 豁免；本人 → 豁免；
目标当前岗位 ∉ MANAGEABLE_ROLES[操作者] → 400；
再走既有 scope.all / 分公司范围判断。
```

- 置于 scope 解析之前：scope.all 的无条件放行正是本次漏洞入口，权线闸必须先于它
- 基于**当前**岗位（`instance.role`）而非请求提交的角色：降级攻击（PATCH director {role: leader}）在请求里带的是权线内角色，只有看当前岗位才能拦住；`'role' in data` 时的 `_validate_role_assignment` 保留，双闸并存

**3. 错误形态沿用 `serializers.ValidationError`（HTTP 400）。**
与既有 `_validate_in_scope` 的「范围外 400」一致（项目惯例：perform_* 内 ValidationError → 400 JSON）；不引入 403 分支。错误文案 `您没有权限管理「{岗位名}」用户`，沿用 `ROLE_CHOICES` 展示名。

**4. scope.all 注释语义同步收窄。**
`_get_user_queryset`（写路径可见集）与 `_validate_in_scope` 的「全部数据=全部用户」表述改为「权线内的任何用户」——get_queryset 仍返回全量（404 隔离不背权线职责），权线由 `_validate_in_scope` 把关，职责分离不变。

## Risks / Trade-offs

- [存量流程若有「manager/director 代改高岗位账号」的实际用法，升级后变 400] → 属漏洞路径本身，宁可拦；如确有合法需求应走 admin 或调整权线表（届时另提变更）
- [manager 同岗互管（可改可删同岗）保留] → 既有设计（互建互管）；删除同岗账号仍受数据范围约束，风险可接受
- [`_validate_role_assignment` 与新闸语义重叠（manager 提交 role=manager 的 director 改单会先被权线闸拦）] → 双闸仅重叠于「带 role 的越权请求」，无冲突判定（都是 400）

## Migration Plan

纯代码变更，无迁移、无数据修正。部署即生效；回滚 = revert 提交。上线后验证：以 manager+全部数据授权账号尝试 PATCH admin 应得 400。
