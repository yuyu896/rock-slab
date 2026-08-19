## 1. 后端：资产汇总台账模型与迁移

- [x] 1.1 在 `apps/assets/models.py` 新增 `AssetStock` 模型（分公司/分公司编号/branch FK/资产编号/资产类目/物品分类/资产名称/规格/数量/警戒线/是否充足，unique_together('分公司','资产编号')，save() 内强制重算是否充足）
- [x] 1.2 生成并执行模型迁移；附带 data migration 按现有 Asset 聚合（分公司+资产编号 Sum 数量，类目/分类/名称/规格取首行、警戒线取 max）生成台账初始行
- [x] 1.3 为 `apps/transfers` 的 Transfer 模型新增可选字段 `固定资产内部编号`（CharField, blank, default=''）并生成迁移

## 2. 后端：台账 API

- [x] 2.1 新增 `AssetStockSerializer`（分公司名解析 branch FK 回填冗余字段，模式同 AssetSerializer；忽略客户端传入的是否充足）
- [x] 2.2 新增 `AssetStockFilterSet`（分公司/资产类目/关键词）与 `AssetStockViewSet`（DataScopeMixin + StandardPagination + OperationPermission，required_operations：create/update/destroy/batch_delete/import → manage_assets）
- [x] 2.3 实现台账 template（8 列：分公司 资产编号 资产类目 物品分类 资产名称 数量 规格 警戒线）与 import（表头列名映射、分公司合法性、≤200 行、(分公司,资产编号) 表内+库内去重报错、是否充足自动计算）action
- [x] 2.4 实现台账 export action（列同表头 10 列，含序号与是否充足）与 batch-delete action
- [x] 2.5 `apps/assets/urls.py` 将 `summary` ViewSet 注册在 `r''` 之前；删除 `AssetViewSet.summary` action

## 3. 后端：回收联动与直接回收

- [x] 3.1 抽取 `_apply_recovery_stock(transfer)`：台账扣减（分公司+资产编号，下限 0，无匹配跳过）→ 明细扣减（优先分公司+资产编号+所属部门=调出部门，回退首条，下限 0 保留记录）→ 固定资产按 `固定资产内部编号` 删除实例；全程 select_for_update + 事务
- [x] 3.2 `TransferViewSet.approve()` 对回收单显式分支调用 `_apply_recovery_stock`（不挂 `_sync_asset` 的 sync_map——其以查到 Asset 记录为前提，FA-only 回收会跳过台账扣减）
- [x] 3.3 `_create_action` 支持 `immediate` 回收：校验 manage_assets 与盘点锁，事务内创建 `审批状态='已通过'` 回收单（审批人=操作者）并即时联动；无权限传 immediate 返回 400
- [x] 3.4 采购/领用/归还/调拨路径确认不触碰 AssetStock（回归检查 + 测试断言）

## 4. 后端测试（pytest）

- [x] 4.1 台账模型测试：唯一约束冲突、是否充足自动重算（新建/编辑/导入/回收扣减各路径）
- [x] 4.2 台账 API 测试：分页筛选、数据范围隔离（admin/授权分公司/无授权）、写操作权限、导入（成功/重复行报错其余导入/分公司非法/超行数）、导出列、batch-delete 越权排除
- [x] 4.3 回收联动测试：审批通过扣台账+重算、无匹配容错、扣减下限 0、明细按调出部门精确匹配与回退、归零保留、FA 按内部编号删除、无内部编号不删 FA、领用归还不动台账
- [x] 4.4 直接回收测试：生成已通过单并即时联动、无 manage_assets 拒绝、盘点锁拒绝、审计日志写入
- [x] 4.5 种子迁移测试：存量明细聚合生成台账行（数量求和、警戒线取 max）

## 5. 前端：API 层与类型

- [x] 5.1 `types/index.ts`：删除 `AssetSummaryRow`，新增 `AssetStock`；`constants/index.ts` 新增 `DEPARTMENT_PRESETS`
- [x] 5.2 `api/assets.ts`：删除 `getAssetSummary`，新增台账 CRUD/batch-delete/import/export/template 函数；`api/transfers.ts`：`recoverAsset` 透传 `immediate` 与 `固定资产内部编号`

## 6. 前端：资产汇总页重写

- [x] 6.1 重写 `views/assets/AssetSummary.vue`：10 列表头、分页连续序号、筛选（分公司/资产类目/关键词）、分页、是否充足不足红色标识、行操作（编辑/填入/删除）
- [x] 6.2 新增 `views/assets/SummaryEditDrawer.vue`（新增/编辑台账行，分公司下拉+编号+类目+分类+名称+数量+规格+警戒线）
- [x] 6.3 新增 `views/assets/SummaryImportDialog.vue`（模板下载+上传+行级错误展示，模式照 AssetImportDialog）
- [x] 6.4 新增 `views/assets/SummaryFillDialog.vue`：单选资产明细/固定资产，预填台账行字段（明细带警戒线），明细用 DepartmentSelect，提交调 createAsset/createFixedAsset，成功提示且不刷新台账数量

## 7. 前端：行内回收与所属部门

- [x] 7.1 新增 `views/assets/RecoveryDialog.vue`：明细模式（数量≤该行数量）/固定资产模式（内部编号随行、数量固定 1），提交 immediate 回收，成功后刷新列表
- [x] 7.2 `AssetList.vue` 与 `FixedAssetList.vue` 行操作区接入「回收」按钮（canManageAssets 可见）并挂 RecoveryDialog
- [x] 7.3 新增 `components/DepartmentSelect.vue`（原生 input+datalist，选项来自 DEPARTMENT_PRESETS，支持自定义输入），替换 `AssetCreatePage.vue` 与 `AssetEditDrawer.vue` 的所属部门 input

## 8. 前端测试（vitest）与回归

- [x] 8.1 DepartmentSelect 组件测试：预置选项渲染、自定义输入 v-model、回显已有值
- [x] 8.2 资产汇总页测试：表头与序号、不足标识、填入弹窗预填与提交调用、导入错误展示
- [x] 8.3 行内回收测试：按钮权限可见性、提交参数（immediate/内部编号/数量上限）
- [x] 8.4 `npm run build`（类型检查）与后端 `pytest` 全量通过；`npm run test` 全量通过

## 9. 部署验证

- [x] 9.1 本地起前后端联调走通：导入台账→填入明细/固定资产→行内回收→台账扣减/FA 记录消失/回收列表留痕
- [x] 9.2 按 deploy.sh 流程部署到生产并验证同路径（含迁移执行成功、种子数据就位）
