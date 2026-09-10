# 分公司筛选支持键入搜索 — 技术设计

## Context

分公司筛选现状：除 Reports.vue 已用 `el-select multiple filterable`（多选、按 id）外，其余筛选位均为原生 `<select class="filter-select">`（单选、值为分公司**名称**、首项「全部分公司」空值）。选项数据源为 `getBranches()`，各页自行拼 `branchOptions`。

生产 72 家分公司，大区级账号下拉查找难。Element Plus 全量引入（main.ts `app.use(ElementPlus)`），el-select filterable 零成本可用，且报表页已有同模式先例。

## Goals / Non-Goals

**Goals:**

- 各列表筛选位的分公司下拉支持键入搜索 + 清空回全部
- 收敛为共用组件，杜绝再散落原生下拉

**Non-Goals:**

- 单据创建页单头分公司（表单输入、值 uuid）——另案跟进
- 报表页多选筛选迁移（现状已可搜索，不动）
- 拼音/首字母检索（中文名包含匹配够用）

## Decisions

### D1：封装 BranchFilterSelect，值语义保持「名称」

`components/BranchFilterSelect.vue`：`el-select filterable clearable`，props `modelValue: string` + `options: { value, label }[]`，内置首项 `''/全部分公司`；`filter-method` 用默认（label 包含匹配）。**值仍为分公司名**——各页 filters.branch 与后端 `branch=` 参数零改动，纯交互替换，回归面最小。不做组件内拉数据：各页数据源与权限口径不同（getBranches 返回的可见范围），由父级传 options，组件保持纯展示。

### D2：样式对齐朴素 filter-select

el-select 通过 CSS 变量/类对齐现口径：高度 38px、圆角 8px、背景 `--color-bg-page`、边框 `--color-border`、字号 `--text-sm`。组件内 scoped 覆盖 `.el-select__wrapper` 相关样式，保证与相邻关键字输入框/重置按钮成排不跳。

### D3：替换点位清单（值与选项拼装不动，只换控件）

- `FixedAssetList.vue`、`AssetSummary.vue`、`AdjustRecordsDialog.vue`、`DepartmentManage.vue`、`Inventory.vue`（及其传 `branchOptions` 的子组件 `InventoryTaskList.vue` 筛选位）、`useTransferList` 使用方（RecoveryList 等列表筛选位）
- 各点仅模板层换控件 + 移除原生 select 的重复拼装（首项「全部」由组件内置，父级不再手工插）

### D4：盘点任务创建页（InventoryTaskCreate）不动

它是表单必选项（无「全部」项、值 uuid），与本次筛选语义不同——归入非目标，与单头分公司同批跟进。

## Risks / Trade-offs

- [el-select 与原生 select 的键盘/焦点细节差异] → filterable 本身即键盘交互，无障碍性不降
- [选项加载慢时键入体验] → options 由父级一次性拉取（72 条量级无感知延迟），非 remote 场景
- [替换面广导致回归] → 每处只换控件不改值语义；vitest 对关键页（实例档案/台账）断言筛选参数与选项渲染不变

## Migration Plan

纯前端，随下次前端构建生效；无数据、无回滚风险。

## Open Questions

（无）
