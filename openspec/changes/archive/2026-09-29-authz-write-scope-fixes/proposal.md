# 组织/权限越权三处修复（authz-write-scope-fixes）

## Why

2026-09-29 对组织架构与权限分配的缺陷排查（两路只读审查 + 高危亲验复核）发现三处越权写缺口：①实例批量维护 `batch-update` 用裸 `in_bulk` 取实例，绕过数据范围——范围外分公司实例的供应商/规格/序列号等可被任意持码用户篡改；②调拨单 `perform_destroy` 漏加「调出方可操作」守护（approve/submit/update 等都有），调入方可删除他人草稿/待审批单；③组织节点的任命字段（`Region.manager`/`Team.leader`/`Branch.manager`）对任何 `manage_organizations` 持有者可写，而「任命即授权」——构成操作码→全量数据范围的提权链；且前端组织弹窗无任命控件却回传旧任命值，存在静默回滚别处任命的路径。

## What Changes

- **批量维护收范围**：`batch-update` 逐实例 `validate_branches_in_scope`，范围外 id 进 `errors`（与「实例不存在」同路径），不再落库修改。
- **调拨删除加守护**：`perform_destroy` 复用既有 `_assert_transfer_operable`（调入方只读、仅调出方可操作），与 update/submit 同口径。
- **任命字段收权 admin**：组织 serializer 校验——非 admin 请求中 `manager`/`leader` 值发生变更（含新建带非空任命）即 400；值未变的普通编辑放行。前端组织弹窗不再回传任命字段（展示保留）。任命 UI 本就仅 admin 可见（权限分配页），口径对齐。
- 测试三组（每修一条一测）+ 回归。

**不混入**（另行拍板）：调拨 `to_branch` 单边校验（修订 3.1 既定设计）、盘点写接口零操作码、流转单创建人校验、孤儿实例等中低项。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `write-authorization-scoping`：范围校验要求补两个场景——实例批量维护的逐实例范围校验（范围外进 errors）；流转单删除纳入调拨「仅调出方可写」口径。
- `position-appointment-permissions`：任命即授权要求补充边界——任命字段的写入/变更仅限 admin，`manage_organizations` 操作码不再隐含任命权。

## Impact

- `backend/apps/assets/views.py`（batch_update 逐实例范围校验）、`backend/apps/transfers/views.py`（perform_destroy 加守护）、`backend/apps/organizations/serializers.py`（任命字段变更校验）。
- `frontend/src/views/Organization.vue`（保存 payload 去除 manager/leader 回传）。
- 对应 pytest/vitest 用例。提案审查两问：无信息双存、无台账数量变动（batch-update 只改实例档案字段不经流转单——现状如此，本变更不扩大其写面），通过。
