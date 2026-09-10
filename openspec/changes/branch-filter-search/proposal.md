# 分公司筛选支持键入搜索

## Why

大区级等数据范围广的账号可见数十家分公司（生产 72 家），而全站分公司筛选除报表页外均为原生 `<select>` 下拉——不支持键入，只能滚动逐条找，第一时间定位困难。报表页（Reports）已是 `el-select filterable` 可搜索，交互模式用户已熟悉，本变更把同一模式推广到其余筛选位。

## What Changes

- 新封装 `BranchFilterSelect` 共用组件：`el-select filterable + clearable`，含「全部分公司」空值项，选中值语义与现筛选一致（空=全部，其余=分公司名）；样式对齐既有 `filter-select` 朴素口径（高度/边框）
- 替换以下筛选位的原生 `<select>`：实例档案（FixedAssetList）、库存台账汇总（AssetSummary）、调整单记录弹窗（AdjustRecordsDialog）、盘点任务列表（Inventory / InventoryTaskList）、部门管理（DepartmentManage）、流转列表（useTransferList 使用方含 RecoveryList 等）
- 键入即按分公司名包含匹配（el-select filterable 默认），清空回到「全部分公司」
- 非目标：单据创建页的单头分公司选择（表单输入，选 uuid，非筛选）——查找难同样存在，另案跟进；拼音首字母检索不做（中文名包含匹配已覆盖主场景）

## Capabilities

### New Capabilities

- `branch-filter-search`: 列表页分公司筛选的可搜索下拉交互（共用组件契约）

### Modified Capabilities

（无——各页筛选行为仅交互升级，值语义与查询口径不变，不改既有能力的要求文本）

## Impact

- **前端**: 新增 `components/BranchFilterSelect.vue`；上述 6+ 处视图/composable 的筛选控件替换；vitest
- 后端、API、查询口径均不动（仍是 branch=名称 的既有过滤参数）
