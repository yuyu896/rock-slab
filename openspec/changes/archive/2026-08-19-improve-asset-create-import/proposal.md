## Why

库存/资产模块在「新增资产」与「批量导入」上存在三处不准确/不便：

1. **所属部门是文本输入**——新增资产表单的「所属部门」为自由文本，易拼写不一致，应改为下拉（固定列表）。
2. **警戒线不联动品目**——资产的「警戒线」现取自导入模板里手填的值，未与「资产分类(品目)」登记的警戒线联动，导致不准确；应按资产编号反查分类的警戒线。
3. **导入模板有序号列**——批量导入模板含「序号」列，导入后用户的序号值会搞乱系统序号；序号应是系统自动排序的行号，且按分公司筛选时随之变化。

## What Changes

1. **所属部门下拉**：`AssetCreatePage` 的「所属部门」由文本输入改为 `<select>`，选项来自固定列表常量 `DEPARTMENT_OPTIONS`（`frontend/src/constants`）。
2. **警戒线联动分类**：
   - 后端 `/api/categories/lookup` 扩展返回 `警戒线`（`warning_line`）。
   - 资产导入：警戒线取自按资产编号反查的分类 `warning_line`，不再读模板列；导入模板移除「警戒线」列。
   - 新增资产表单：资产编号失焦联动时一并带出「警戒线」（复用 `useAssetCodeAutofill`，扩展其带出字段）。
3. **序号自动排序**：
   - 资产列表「序号」列改为当前筛选/分页内的**行序号**（`(page-1)*pageSize + 行内序 + 1`，随分公司筛选变化），不显示存储值。
   - 批量导入模板移除「序号」列；导入不再读序号，自动分配存储序号（保持默认排序）。

## Capabilities

### New Capabilities
- `asset-create-import`: 资产新增表单与批量导入的准确性改进——所属部门下拉、警戒线按编号联动分类、序号改为自动行序号。

### Modified Capabilities
<!-- 复用既有 asset-code-autofill（lookup）能力，扩展其带出字段（警戒线）；该能力尚未归档，不单列 MODIFIED。 -->

## Impact

- **后端** `apps/categories/views.py`（lookup 返回警戒线）、`apps/assets/views.py`（导入模板去序号/警戒线列；导入逻辑：序号自动分配、警戒线取自分类）。
- **前端** `AssetCreatePage.vue`（所属部门下拉 + 警戒线联动）、`AssetList.vue`（序号改行序号）、`composables/useAssetCodeAutofill.ts`（带出警戒线）、`constants`（`DEPARTMENT_OPTIONS`）。
- **测试**：lookup 返回警戒线；导入序号自动分配、警戒线取自分类；模板无序号/警戒线列。
- 无 DB 迁移（不改动模型字段，仅改导入/展示逻辑）。
