# 组织/权限越权三处修复 — 技术设计

## Context

缺陷排查结论（均带 file:line 证据并亲验）：`assets/views.py:501` 的 `batch_update` 以 `FixedAsset.objects...in_bulk(ids)` 取实例，未过数据范围；`transfers/views.py:447` 的 `perform_destroy` 未调用 `_assert_transfer_operable`（该守护已用于 approve/submit/resubmit/withdraw/update，语义「transfer 类型仅调出方可操作」）；`organizations/serializers.py` 三个任命字段全可写，ViewSet 仅要求 `manage_organizations`。

## Goals / Non-Goals

**Goals:** 三处越权写关闭；任命权收口到 admin；修复不改变任何合法用户现有操作路径。

**Non-Goals:** 不动修订 3.1 的调拨单边校验设计；不补盘点写操作码（中危项另行提案）；不做任命审批流。

## Decisions

### D1：批量维护逐实例 `validate_branches_in_scope`（而非预过滤 queryset）

`in_bulk` 后对每个实例调 `validate_branches_in_scope(request.user, inst.branch)`，越界实例进 `errors`（文案「分公司不在授权范围」，与导入口径一致）。备选「按 branch__in 预过滤」会把范围外 id 误报为「实例不存在」，语义失真，弃。管理员豁免由 validate 内建（scope.all）。

### D2：调拨删除复用 `_assert_transfer_operable`

一行守护调用，非 transfer 类型直接放行（守护自身短路），错误文案沿用「调入方分公司对此调拨单只读，仅调出方分公司可操作」。与 update/submit 完全同口径，无新语义。

### D3：任命字段「非 admin 不可变更」（而非 serializer 只读）

三个 serializer 的 `validate()`：非 admin 且（新建带非空任命 或 任命值 ≠ 实例现值）→ 400「任命/免任仅系统管理员可操作」；值未变（含 null→null）放行。admin 不受限。

理由：serializer 只读会一并废掉 admin 经同一 API 的任命路径（权限分配页正是走组织 API 写任命字段，且该页本就仅 admin 可见）。「不可变更」口径让非 admin 的节点普通编辑（名称/编码/地址/状态）不受影响。
备选「新增 appoint 操作码」：13 码体系外的扩码需模板/种子/矩阵三处联动，超出安全修复范畴，弃（记录为后续可演进方向）。

### D4：前端组织弹窗停止回传任命字段

`Organization.vue` 三个 payload 删除 `manager`/`leader` 键（弹窗本无任命控件，回传只有风险没有功能）；编辑表单的负责人**展示**保留。这样 D3 上线后 director（持 manage_organizations）编辑组织节点不会因隐藏字段触发 400。

## Risks / Trade-offs

- [存量调用方带任命字段 PATCH] → 非 admin 且值未变：放行（D3 只拒变更）；值变：400 属预期拦截。前端 D4 同步消除误伤面。
- [任命场景测试依赖 director 写 manager] → pytest 现有用例若按旧口径构造，需改为 admin 构造；逐一排查更新。
- [position-appointment spec 中 manager 模板 8 项陈述过时] → 系 manager-grants-tighten 未归档所致，本变更不动该段，归档链收口时自愈；在归档备注中提醒。

## Migration Plan

纯后端行为收紧 + 前端小改，无数据迁移；部署即生效。上线后验证：admin 任命路径正常、director 编辑组织节点正常、三类越权请求被拒。

## Open Questions

（无——三处修法与「任命=admin 专属」口径已在缺陷清单评审中与用户对齐方向；如对 D3 的 admin-only 口径有异议，提案阶段提出。）
