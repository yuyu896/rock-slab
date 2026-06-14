## Why

固定资产表（`/fixed-assets`）当前只显示 10 列（内部编号、资产编号、资产名称、序列号、供应商、使用人、所属部门、分公司、状态、操作），不符合公司业务需要的信息密度。公司希望该表展示完整的 19 列资产信息，将父级 Asset（品目）的关键字段通过外键关联一并展示。

## What Changes

将固定资产表的列从 10 列扩展为 19 列，列顺序与数据来源如下：

序号、分公司编号、分公司、资产编号、资产类目、物品分类、资产名称、电脑序列号、供应商、入库日期、是否租用、数量、规格、单价、购入金额、出库日期、所属部门、使用人、当前状态

同步修改 4 个地方，保持一致：
- **表格表头**：`FixedAssetList.vue` 显示 19 列
- **新增表单**：弹窗字段扩展，覆盖实例可编辑字段
- **导出 Excel**：后端 `FixedAssetViewSet` 新增 export action，导出 19 列
- **导入模板 + 导入解析**：后端模板改为 19 列表头，导入逻辑按列位置解析（父品目字段只读，从关联品目继承；实例字段写入）

## Capabilities

### New Capabilities

- `fixed-asset-table-columns`: 固定资产表的完整列定义与数据来源映射，覆盖表格展示、导出、导入模板、新增表单的一致性

### Modified Capabilities

## Impact

**后端**：
- `backend/apps/assets/serializers.py` — `FixedAssetSerializer` 增加父级 Asset 字段
- `backend/apps/assets/views.py` — `FixedAssetViewSet` 新增 export action、修改 import template 表头、修改 import_excel 解析逻辑

**前端**：
- `frontend/src/views/FixedAssetList.vue` — 表头 19 列、单元格绑定、新增表单字段扩展、空状态 colspan
- 前端导入模板（`FixedAssetList` 用后端 `/api/assets/fixed-assets/template`）无需改前端

**数据模型**：不改模型字段，仅通过 `FixedAsset.asset` 外键关联读取父级 Asset 字段
