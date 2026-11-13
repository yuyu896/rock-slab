## Why

当前系统存在三个独立但同属"数据录入与导出体验"的小问题：移动员工时分公司必选，无法处理无分公司归属的员工；实例档案导出缺少备注与管理方式两列，导出数据不完整；新增单据选择品目时无法按管理方式筛选，且用户不知道已支持按名称搜索。三者都是用户实际使用中遇到的卡点，合并为一个变更统一修复。

## What Changes

- **组织架构移动员工：分公司改为可选**（**BREAKING** 针对现有 spec 约束）。移动弹窗的分公司由必选改为可选并支持清空，允许将员工移动到无分公司归属状态。区域/行政组级联保留，但提交不再强制校验分公司。
- **实例档案导出补字段**。固定资产导出在现有 13 列（序号、分公司、内部编号、品目编号、品目名称、规格、序列号、当前状态、使用人、部门、入库日期、供应商、采购日期）基础上，新增「备注」「管理方式」两列，共 15 列。
- **ItemPicker 增加管理方式筛选 + 名称搜索提示**。品目选择组件新增「管理方式」筛选下拉（透传至后端），并在搜索框增加 placeholder 提示用户支持按编号或名称搜索。

## Capabilities

### New Capabilities
- `item-picker-management-filter`: 品目选择组件（ItemPicker）支持按管理方式筛选品目列表，并在搜索框以 placeholder 提示用户支持按编号或名称搜索

### Modified Capabilities
- `unified-organization-page`: 移动员工弹窗的分公司由必选改为可选（允许清空），以支持无分公司归属员工的移动操作
- `fixed-asset-export`: 导出列新增「备注」「管理方式」两列，与实例表列布局保持一致

## Impact

- **后端**：`backend/apps/assets/views.py` 导出逻辑（`FA_EXPORT_HEADERS` 及行数据组装）增加两列字段映射；ItemPicker 依赖的品目列表接口需支持按管理方式过滤参数。
- **前端**：`frontend/src/views/Organization.vue` 移动弹窗表单校验放宽（分公司非必选、可清空）；`frontend/src/components/ItemPicker.vue` 新增管理方式下拉 + placeholder 提示。
- **契约影响**：导出 Excel 列数从 13 增至 15，依赖导出文件的下游（若有）需感知新列；移动员工不再强制写 branch，后端 `branch` 字段已为 nullable，无需迁移。
- **无数据库迁移**：三处改动均不涉及模型字段新增或修改。
