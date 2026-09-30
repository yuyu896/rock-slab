## Why

安全审计动态复现（pytest 隔离库实测）：manager 仅凭 `manage_users` 操作码 + 「全部数据」范围授权，即可 PATCH 200 修改 admin 账号、DELETE 204 删除 admin 账号。根因是 `_validate_in_scope` 只校验数据范围、从不比较岗位等级——`MANAGEABLE_ROLES` 只拦「请求带 role 字段」的分配场景，不带 role 的更新与删除完全绕过。同分公司内 manager 改 director 同样放行，且存在降级攻击变体：manager PATCH director 把 role 改成 leader 时只校验目标角色在权线内、不校验被改者当前岗位，一样能过。

## What Changes

- 更新/删除用户新增**目标岗位权线校验**：目标用户岗位必须 ∈ 操作者 `MANAGEABLE_ROLES` 权线（admin 豁免、本人豁免），不满足返回 400 且不落库
- 校验基于目标用户**当前**岗位、置于既有范围校验之前——同一道闸同时封堵越权改/删与降级攻击
- 「全部数据」授权的管理语义收窄为「权线内的任何用户」，不再无条件全量
- 补齐越权测试：改/删 admin、同分公司改 director、降级攻击、同岗互管回归、director 权线边界、admin 与本人豁免

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `personnel-management`: 更新/删除用户在既有数据范围校验之上新增岗位权线校验要求；「全部数据」授权的管理范围语义收窄为权线内

## Impact

- `backend/apps/users/views.py`：`_validate_in_scope` 加入 `MANAGEABLE_ROLES` 目标岗位检查，注释同步
- `backend/tests/test_users.py`：新增越权与回归用例
- API 行为变化：原先 200/204 的跨权线写请求变为 400（前端人员管理页不提供跨权线入口，无适配需要）
- 无数据库迁移、无前端改动
