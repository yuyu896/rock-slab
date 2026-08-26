## Why

2026-08-25 对照总设计书的五路契约审计确认 4 条高危缺陷：写路径范围校验缺口（调整单/台账导入/流转导入/盘点可越权改写或读取范围外分公司台账）、盘点任务可经 PATCH 绕过状态机与范围、采购数量管理品目逐件生成实例档案（污染实例层并使生产 15 条存量警告持续增长）、品目「管理方式」可无守卫切换（反向切换直接引爆对账非零退出、卡死部署）。审计中「处置单缺失」经用户拍板确认为不需要（处置决策在回收时刻作出），不在本提案范围。

## What Changes

- 台账调整单创建 API 补 `validate_branches_in_scope`：目标分公司越界返回 400 不落账（现仅凭全局操作码 `adjust_ledger`/`manage_assets` 放行，分公司 id/名称任意传）。
- 台账增量导入预览与确认两阶段均校验分公司范围：范围外行整行拒绝并提示，预览不再泄露范围外现值。
- 流转 Excel 导入补范围校验：调出/调入分公司任一越界的行拒绝（对照表单路径已有实现）。
- 盘点任务加固：`branch` 创建时必填且校验范围；`branch`/`status` 列为只读，PATCH 不得改挂分公司或绕状态机直改状态。
- 采购自动生成实例补管理方式守卫：`generate_instances` 仅对实例管理品目执行，数量管理品目采购生效只动台账不产实例。
- 品目「管理方式」切换守卫：品目挂有实例档案或台账任一数量列非零时，`management_type` 禁改并返回可操作的错误提示（先清档/对齐再切换）。
- 前端配套：盘点创建表单分公司改为必选（与后端必填一致）；品目编辑弹窗在受锁定的品目上禁用管理方式下拉并显示原因。
- 每项修复配回归测试（含审计指出的测试盲区：采购数量品目断言实例数为 0）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `write-authorization-scoping`：「写操作必须校验目标分公司在授权范围」的适用面从流转创建/盘点创建扩展至台账调整单创建、台账增量导入（预览与确认）、流转 Excel 导入；新增盘点任务 `branch` 必填与 `branch`/`status` 不可经更新接口修改的防绕过要求。
- `document-instance-binding`：采购生效自动生成实例的规则收窄——仅实例管理品目逐件生成，数量管理品目不生成实例档案。
- `item-dictionary`：新增「管理方式」切换约束——有实例档案或非零台账存量的品目 MUST NOT 切换管理方式，须先清档/对齐。

## Impact

- 后端：`apps/assets/views.py`（调整单 create、导入 import_excel）、`apps/transfers/views.py`（导入 import_excel）、`apps/inventories/serializers.py`（branch 必填 + 只读字段）与 `views.py`、`apps/assets/services/instances.py`（generate_instances 守卫）、`apps/categories/serializers.py`（management_type 切换校验）。
- 前端：`views/inventory/InventoryTaskCreate.vue`（分公司必选）、`views/categories/CategoryCreate.vue`（管理方式锁定提示）。
- 测试：`tests/test_write_scope.py`、`test_ledger_contract.py`、`test_management_permissions.py` 等。
- 不改数据库结构（盘点 branch 的 DB 可空保持，收紧在序列化层；存量无 branch 盘点任务如有则视为脏数据由测试固定为不存在）。
