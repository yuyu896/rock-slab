## 1. 台账写路径范围校验（assets）

- [ ] 1.1 `LedgerAdjustmentViewSet.create`（apps/assets/views.py）：解析出 branch 后调用 `validate_branches_in_scope(request.user, branch)`，越界 400 不落账（id 与名称两种指定方式都在校验之后才生效）
- [ ] 1.2 台账增量导入 `_parse_import_rows` / `import_excel`（apps/assets/views.py）：branch_map 改按用户授权范围构建（admin 全量），范围外行进 `errors`（提示「分公司 X 不在你的授权范围」）、不进 diffs；确认阶段因此天然只入账合法行
- [ ] 1.3 回归测试（tests/test_write_scope.py 或新文件）：范围仅 A 的 adjust_ledger 用户 ① POST 调整单目标 B → 400 且 B 台账不变、无调整单生成；② 上传含 B 行的台账文件 → diffs 不含 B 行且不返回 B 现值、B 行进 errors、confirm 仅入账 A 行；admin 豁免两例

## 2. 流转导入范围校验（transfers）

- [ ] 2.1 `import_excel`（apps/transfers/views.py）：逐行建单前对调出/调入分公司调用 `validate_branches_in_scope`，越权行 catch 后进该接口既有的行级 `errors`（提示不在授权范围），不建单、合法行照常
- [ ] 2.2 回归测试：范围仅 A 的 manage_assets 用户导入含「调出分公司=B」行的调拨文件 → B 行进 errors 不建单、A 行正常建待审批单

## 3. 盘点任务加固（inventories）

- [ ] 3.1 `InventoryTaskSerializer`（apps/inventories/serializers.py）：`branch` 设为必填（create 校验缺失 400），`branch` / `status` 加入 read_only_fields（PATCH 静默忽略，状态机动作经 `_transition` 不受影响）
- [ ] 3.2 核对调用面：grep 前端全部盘点创建入口（PC `InventoryTaskCreate.vue` 及可能的移动端）与盘点 PATCH 调用，确认无传空 branch / 依赖 PATCH 改字段的用法；`InventoryTaskCreate.vue` 分公司改为必选（表单校验 + 必填标识）
- [ ] 3.3 回归测试：① POST 盘点缺 branch → 400；② PATCH `{"branch": B, "status": "completed"}` → 两字段保持原值、任务状态不越级、无调整单生成；③ 非 admin 建范围内分公司任务照常成功（不误伤）

## 4. 采购生成实例的管理方式守卫（assets/services）

- [ ] 4.1 `generate_instances`（apps/assets/services/instances.py）：函数开头加守卫——`line.item.management_type != 'instance'` 直接返回 `[]`（守卫贴近生成逻辑，未来调用方自动受保护）
- [ ] 4.2 补审计盲区断言（tests/test_ledger_contract.py）：现有采购用例（数量品目 ×10）断言生效后该品目 `FixedAsset` 计数为 0；新增实例管理品目采购用例断言实例数 == 数量（双口径）
- [ ] 4.3 回归测试：数量品目采购审批通过 → 台账在库 +N 正常、实例数不变（对应 spec 场景「数量管理品目采购不生成实例」）

## 5. 品目管理方式切换守卫（categories）

- [ ] 5.1 `CategorySerializer`（apps/categories/serializers.py）：新增判定函数（挂 FixedAsset 或 AssetStock 任一列 > 0），`update` 中 `management_type` 变更且判定为真时 400，提示存量状况与解锁路径；序列化输出派生只读布尔 `management_locked`
- [ ] 5.2 前端 `CategoryCreate.vue` 编辑模式：`management_locked` 为真时禁用管理方式下拉并显示锁定原因（提交后端 400 兜底）
- [ ] 5.3 回归测试（tests/test_categories.py 或新文件）：① 挂实例品目改回数量管理 → 400；② 台账非零品目改实例管理 → 400 且对账不受影响；③ 无存量品目切换成功且 `management_locked` 输出正确

## 6. 回归收尾

- [ ] 6.1 全量回归：`pytest` 全绿 + `npm run test` + `npm run build`（类型检查门禁）+ `python manage.py check_ledger_consistency`
- [ ] 6.2 对照验收手册盘点章节核对分公司必选的新交互说明（如手册有对应步骤需同步一句话）
