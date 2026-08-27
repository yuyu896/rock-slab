## 1. 后端：immediate 通道下线

- [x] 1.1 `_create_action` 删 immediate_recovery 分支（权限校验/直接落已通过/创建后 `_apply_ledger`），开头对携带 `immediate` 的请求返回 400（文案引导走回收单审批流、数据修正走台账调整单），不落库
- [x] 1.2 `tests/test_recovery_stock_link.py` 用例组改造（映射见 design D3）：删 immediate 三语义用例与无权限用例；盘点锁用例改写为普通回收单创建遇锁 400；保留 stays_pending；新增 immediate 拒绝用例（普通用户与持 manage_assets 用户均 400 且不落库）

## 2. 前端：删行内回收入口

- [x] 2.1 `FixedAssetList.vue` 删回收按钮（:291 区域）、`RecoveryDialog` 挂载与 import、`openRecovery`/`showRecoveryDialog`/`recoveringAsset` 状态
- [x] 2.2 删 `views/assets/RecoveryDialog.vue` 与 `tests/views/RecoveryDialog.test.ts` 文件
- [x] 2.3 `api/transfers.ts` `recoverAsset` 删 `immediate` 参数类型（函数保留，RecoveryCreate 在用）

## 3. 验证与收尾

- [x] 3.1 后端 `pytest` 全绿
- [x] 3.2 前端 `npm run build`（类型门禁）+ `npm run test` 全绿
- [x] 3.3 feat + openspec 两个 commit → push → 归档 change（5 个主 specs 同步），v2-revision-draft.md 第 4 案状态改 ✅
