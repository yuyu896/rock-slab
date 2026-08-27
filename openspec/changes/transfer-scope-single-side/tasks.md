## 1. 后端：创建/编辑单边化（修订 3.1 前半）

- [x] 1.1 `_create_action`：action_type == transfer 时 `validate_branches_in_scope(user, from_branch)` 只校验调出方；其余类型维持双边；流转 Excel 导入的调拨行同口径（导入建单是创建路径，注释自陈"与表单路径同源"）
- [x] 1.2 `update`（编辑已驳回）：同构按类型分支（编辑后单据的调出/调入分公司）
- [x] 1.3 后端测试：A 范围用户建 from=A to=B 调拨 201（原 400）；from=B 调拨 400；非调拨类型（如 return to=B）仍 400（用例补入 test_write_scope.py / test_transfers.py）

## 2. 后端：调入方只读硬边界 + canOperate

- [x] 2.1 `TransferViewSet` 新增 `_assert_transfer_operable(user, transfer)`（仅 transfer 类型且非 all 时校验 from_branch 在范围，报错文案「调入方分公司对此调拨单只读」），挂载 approve / submit / resubmit
- [x] 2.2 `get_serializer_context` 解析一次 `resolve_user_scope(request.user)` 传入 serializer；`TransferSerializer` 增只读 `canOperate`（transfer = all 或 from_branch 在范围；其余类型恒 true；无 context 默认 true）
- [x] 2.3 后端测试：调入方 approve/submit/resubmit 调入调拨 400、调出方 200；编辑路径调入方 400；列表 canOperate 断言（调入方 false / 调出方 true / 非 transfer 类型 true）；调入方列表可见性回归（scope_transfer_fields）

## 3. 前端：按 canOperate 显隐

- [x] 3.1 `types` Transfer 增 `canOperate?: boolean`；TransferList.vue 操作列写按钮（通过/驳回）`v-if="item.canOperate !== false"`，详情按钮不隐藏
- [x] 3.2 TransferDetail.vue 审批操作条按 `canOperate` 显隐
- [x] 3.3 mobile/ApprovalList.vue 通过/驳回按钮叠加 `canOperate` 判断
- [x] 3.4 前端测试（vitest 可覆盖处）：canOperate=false 时列表/详情渲染不含操作按钮

## 4. 验证与收尾

- [x] 4.1 后端 `pytest` 全绿
- [x] 4.2 前端 `npm run build`（类型门禁）+ `npm run test` 全绿
- [ ] 4.3 feat + openspec 两个 commit → push → 归档 change，v2-revision-draft.md 第 3 案状态改 ✅
