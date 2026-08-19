## 1. 数据库模型变更

- [x] 1.1 Transfer 模型新增字段：供应商(CharField)、单价(DecimalField)、总金额(DecimalField)、需求部门(CharField)、采购经办人(CharField)、用途(CharField)
- [x] 1.2 Transfer 模型 APPROVAL_CHOICES 新增 ('已入库', '已入库')
- [x] 1.3 运行 makemigrations 和 migrate 生成并应用迁移

## 2. 后端 API — 入库操作

- [x] 2.1 新增 `POST /api/transfers/{id}/warehouse` 端点，验证 purchase 类型且 已通过 状态，执行入库逻辑
- [x] 2.2 入库逻辑：创建或更新 Asset 记录（按资产编号匹配），设置入库日期，更新状态为 已入库
- [x] 2.3 TransferSerializer 中包含新增字段，审批状态选项包含 已入库

## 3. 后端 API — 按类型区分模板/导入/导出

- [x] 3.1 `download_template` 端点按 `type` 参数返回对应类型的模板（purchase/assign/transfer 各自列定义）
- [x] 3.2 `import_excel` 端点按 `type` 参数使用对应列映射解析数据
- [x] 3.3 `export_excel` 端点按 `type` 参数使用对应列定义导出（领用导出额外计算部门累计领用和当前库存）

## 4. 前端模板定义

- [x] 4.1 `importTemplate.ts` 新增 PURCHASE_HEADERS（14列）、ASSIGN_HEADERS（7列），重定义 TRANSFER_HEADERS（14列，去掉流转类型列）
- [x] 4.2 `generateTransferTemplate` 改为按 type 参数选择对应 headers 生成模板

## 5. 前端入库按钮

- [x] 5.1 PurchaseList.vue 中审批通过且未入库的记录显示"入库"操作按钮
- [x] 5.2 新增 `warehouseTransfer` API 调用函数（`api/transfers.ts`）
- [x] 5.3 点击入库按钮调用 API，成功后刷新列表

## 6. 验证

- [x] 6.1 分别下载三种模板，确认列定义符合产品说明书
- [x] 6.2 导入采购模板数据，审批通过后点击入库，确认 Asset 记录创建成功
- [x] 6.3 导入领用和调拨模板数据，确认正确创建对应类型的流转记录
