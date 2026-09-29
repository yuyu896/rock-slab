# 权限加固第二批 — 实施任务

## 1. 盘点写接口挂码

- [x] 1.1 `inventories/views.py` 类级 `required_operations` 字典补齐：create/update/partial_update/destroy/start/check/check-instance/submit/recount/cancel/import-result → `manage_assets`（approve/reject 维持 `approve_inventory`，GET 类不动）
- [x] 1.2 pytest：无码用户建盘点/启动/导入 403；持 manage_assets 正常；审批动作口径不回归

## 2. 流转单归属

- [x] 2.1 `transfers/views.py` 新增 `_assert_owner_or_admin`，挂 update/partial_update/destroy/submit/resubmit/withdraw；approve/reject 不动
- [x] 2.2 pytest：非创建人（同范围）update/destroy/submit 403；创建人 resubmit 放行；admin 不受限；审批人 approve 不因归属被拦

## 3. 低危杂项

- [x] 3.1 清理 `required_operations` 中 `warehouse` 死配置；`tests/test_write_scope.py` 相关断言改写为存活动作
- [x] 3.2 `users/views.py` create/update 追加校验 payload 中 branch 新值在操作者范围（admin/全部数据豁免）+ 用例
- [x] 3.3 `assets/views.py` batch-update：`inst.branch is None` → errors「未归属分公司」+ 用例

## 4. 前端权限刷新

- [x] 4.1 路由 afterEach 节流（≥5 分钟）静默重拉 `permissions/me`（失败不打扰）

## 5. 验证与收口

- [x] 5.1 后端 `pytest` 全绿、前端 `npm run test` + `npm run build` 过
- [ ] 5.2 手验清单：无码账户建盘点 403 / manager 正常；他人单据改删 403 / 创建人正常；本地验证后自行部署
