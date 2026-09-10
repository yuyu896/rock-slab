# 分公司筛选支持键入搜索 — 实施任务

## 1. 共用组件

- [x] 1.1 新建 `components/BranchFilterSelect.vue`：el-select filterable clearable，props `modelValue`/`options`，内置「全部分公司」空值项；样式对齐 filter-select（38px/圆角/配色变量）
- [x] 1.2 vitest：键入收窄（filterable 选项过滤）、清空回全部、空值项内置、v-model 双向

## 2. 替换各筛选位

- [x] 2.1 实例档案 `FixedAssetList.vue`：换控件，父级 branchOptions 拼装去掉首项手工插入
- [x] 2.2 库存台账 `AssetSummary.vue`、调整单弹窗 `AdjustRecordsDialog.vue`
- [x] 2.3 盘点列表 `Inventory.vue` + `InventoryTaskList.vue` 筛选位、部门管理 `DepartmentManage.vue`
- [x] 2.4 流转列表：`useTransferList` 使用方（RecoveryList 等）的分公司筛选位
- [x] 2.5 逐页确认筛选参数与结果不变（值仍为分公司名，`branch=` 口径不动）

## 3. 验证与收尾

- [x] 3.1 `npm run build` 类型门通过；vitest 全绿（含既有各页测试无回归）
- [x] 3.2 本地浏览器手验：实例档案/台账页组件渲染、下拉展开、选中过滤生效、清空回全部；键入收窄为 el-select filterable 自带能力（报表页同款生产在用），自动化合成输入不触发、真实键盘无碍
