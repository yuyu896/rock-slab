## Context

资产流转页面（Transfer.vue）目前通过 6 个 action 端点（purchase/assign/return/transfer/repair/scrap）逐条创建流转单。后端 `TransferViewSet` 是 `ModelViewSet`，但没有 import/export action。前端 `transfers.ts` 也缺少对应的批量操作 API。

Transfer 模型字段为中文（调拨日期、调出分公司、资产编号、调拨数量等），action_type 区分流转类型。导入时 Excel 每行需指定 action_type 列。

## Goals / Non-Goals

**Goals:**
- 后端新增 `import_excel` 和 `export_excel` action
- 前端新增批量导入按钮和弹窗（与资产列表批量导入风格一致）
- 导入模板包含所有必要字段，action_type 列提供可选项

**Non-Goals:**
- 不修改现有流转提交逻辑
- 不实现导入预览/编辑功能
- 不实现流转记录的审批状态导入（默认为"待审批"）

## Decisions

1. **后端 import 参考 assets 的实现** — 使用 openpyxl 解析，返回 `{ imported, errors }` 格式
2. **Excel 模板字段**：调拨日期、action_type（领用/归还/调拨/维修/报废/采购入库）、调出分公司、调出部门、调入分公司、调入部门、资产编号、资产名称、规格型号、调拨数量、调拨原因、调出负责人、调入负责人、备注
3. **action_type 映射** — Excel 中使用中文标签（领用/归还/调拨/维修/报废/采购入库），后端自动转换为 action_type 值
4. **导出复用为模板** — export 导出空表头即可作为导入模板使用
5. **前端复用 AssetList 的弹窗模式** — 三步式（下载模板 → 上传 → 结果），保持一致体验

## Risks / Trade-offs

- [action_type 拼写错误导致导入失败] → 后端做中文→英文映射，映射不到的行报错提示
- [大文件上传可能超时] → 设置较长 timeout（60s），前端显示 loading
