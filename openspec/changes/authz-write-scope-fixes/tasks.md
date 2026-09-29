# 组织/权限越权三处修复 — 实施任务

## 1. 后端三处修复

- [x] 1.1 `assets/views.py` batch_update：`in_bulk` 取实例后逐个 `validate_branches_in_scope(request.user, inst.branch)`，越界实例进 `errors`（文案「分公司不在授权范围」），不落库修改
- [x] 1.2 `transfers/views.py` perform_destroy：调用 `_assert_transfer_operable(request.user, instance)`（置于已生效状态检查前后皆可，口径与 update/submit 一致）
- [x] 1.3 `organizations/serializers.py` 三个 serializer 的 `validate()`：非 admin 且任命字段（Region/Branch 的 manager、Team 的 leader）值变更或新建非空 → 400「任命/免任仅系统管理员可操作」

## 2. 前端配套

- [x] 2.1 `Organization.vue` 三个保存 payload 删除 `manager`/`leader` 回传键（编辑表单负责人展示保留），避免非 admin 编辑触发 400

## 3. 测试

- [x] 3.1 pytest：范围外实例 batch-update 进 errors 不改；调入方 DELETE 调拨单 400、调出方可删草稿；非 admin 变更任命 400、值未变放行、admin 任命成功；既有任命类用例按新口径排查修正
- [x] 3.2 前端全量 `npm run test` + 类型门禁 `npm run build` 通过；后端 `pytest` 全绿

## 4. 收口

- [ ] 4.1 手验清单：admin 走权限分配页任命/改任正常；director 编辑组织节点（名称/编码）正常；本地验证后自行部署
- [ ] 4.2 归档时备注：position-appointment spec 中 manager 模板 8 项陈述由 manager-grants-tighten 归档链修正，勿在本变更重复处理
