# 权限加固第二批：盘点挂码 + 流转单归属 + 低危杂项（authz-hardening-2）

## Why

2026-09-29 缺陷排查的中低危项，用户已逐项拍板：①盘点模块除 approve/reject 外全部写接口未声明操作码——仅有任命、无任何 OperationGrant 的用户可建盘点（锁死该分公司全部流转）、作废/删除他人任务、导入盘点结果；②流转单 update/destroy/submit/resubmit/withdraw 无归属校验，范围内任何人可改删他人单据（拍板：仅创建人+admin）；③低危杂项：warehouse 死配置、改用户分公司无范围校验、无分公司实例静默穿过写校验、前端权限变更需刷新才生效。

**不含**调拨 to_branch 单边问题——用户拍板走「单边+调入方驳回通道」新功能，另立变更（transfer-reject-channel）。

## What Changes

- **盘点写接口挂 `manage_assets`**：create/update/destroy/start/check/check-instance/submit/recount/cancel/import-result 补声明（approve/reject 维持 `approve_inventory`，GET 类不动）。不加新操作码、不动岗位模板（manager/leader 模板已含 manage_assets）。
- **流转单归属收紧**：update/destroy/submit/resubmit/withdraw 要求 `created_by` 为本人或 admin（approve/reject 的审批权口径不变）；导入建单的 created_by=导入操作者。
- **杂项**：清理 required_operations 中不存在的 `warehouse` 条目（含测试同步）；用户管理 create/update 校验**提交的目标分公司**在操作者范围（现仅校验目标用户现属）；batch-update 对 `branch=None` 实例报「未归属分公司」进 errors（不动全局 validate——其 None 跳过被"可选无调入方"等语义依赖）；前端路由切换时节流（≥5 分钟）静默重拉 `permissions/me`，权限变更无需手动刷新。
- 测试：盘点 403/放行、归属 403/放行（创建人/admin/导入单）、杂项各一条；全量回归。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `write-authorization-scoping`：敏感写声明要求补盘点场景；范围校验要求补用户管理目标分公司与无分公司实例两场景；新增「流转单写操作归属（仅创建人与 admin）」需求。

## Impact

- `backend/apps/inventories/views.py`（操作码声明）、`backend/apps/transfers/views.py`（归属 helper + warehouse 清理）、`backend/apps/users/views.py`（分公司校验）、`backend/apps/assets/views.py`（batch-update 孤儿拦截）。
- `frontend/src/router/index.ts` 或 `MainLayout.vue`（节流重拉）、`backend/tests/test_write_scope.py` 等同步。
- 不动操作码体系、岗位模板、种子/门禁。提案审查两问：无信息双存、无台账数量变动（归属/挂码只影响准入不改写入路径），通过。
