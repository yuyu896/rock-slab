## Why

2026-08-27 验收发现创建调拨单要求同时持有调出、调入两家分公司授权（v2-revision-issues.md 议题 5，定案于 v2-revision-draft.md 修订 3.1 并已入设计书修宪记录）：实现时自选了最严一档双边校验，小组织跨范围调拨常由单边发起，双边强校验阻断正常业务。定案为**只校验调出方权限；调入方对该单据只读可见**。本案为拆案计划（v2-revision-draft.md §八）第 3 案，落实修订 3.1。

## What Changes

- **创建/编辑调拨单只校验调出方**：`transfer` 类型单据的 `validate_branches_in_scope` 调用只传 from_branch（调入分公司不要求授权）；其余四种类型（purchase/assign/return/recovery）维持现状校验。前端创建页调入分公司下拉本就是全量字典，无需改动。
- **调入方只读**：调拨单对调入方用户收紧写操作——审批（通过/驳回）、草稿提交、驳回后重新提交、驳回后编辑，凡 `transfer` 类型均要求操作者授权范围含**调出分公司**（admin/全量授权豁免）；调入方对这些单据仅可见不可操作。列表可见性本身已由 `scope_transfer_fields` 双向过滤实现（现状保留）。
- **前端按 canOperate 显隐操作按钮**：流转单序列化器增 `canOperate` 只读字段（transfer 类型 = 范围含调出方，其余类型恒 true）；PC 调拨列表/详情与移动端审批中心的写操作按钮按该字段显隐，调入方视角不出现可操作入口。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `write-authorization-scoping`: 「写操作必须校验目标分公司在授权范围」条文增加调拨例外——transfer 类型仅校验调出分公司；新增「调拨单调入方只读」requirement（写操作仅调出方 + canOperate 字段 + 前端显隐）。

## Impact

- **后端**：`apps/transfers/views.py`（`_create_action`/`update` 按类型传参、新增调出方操作权校验 helper、serializer context 传 scope）、`apps/transfers/serializers.py`（增 `canOperate`）。无模型/迁移变更。
- **前端**：`views/transfers/TransferList.vue`（操作列按 canOperate 显隐）、`views/transfers/TransferDetail.vue`（审批按钮显隐）、`views/mobile/ApprovalList.vue`（通过/驳回按钮显隐）、`types`（Transfer 增 canOperate）。
- **测试**：后端 `tests/test_write_scope.py`/`test_transfers.py` 补调拨单边创建、调入方写操作 400、canOperate 断言；前端 `npm run build` 类型门禁。
- **兼容**：调入方此前对跨范围调拨本就无法创建（双边校验拒），收紧写操作不破坏任何现存合法路径；`canOperate` 为增量字段。
