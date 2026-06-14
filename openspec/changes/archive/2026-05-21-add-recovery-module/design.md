## Context

当前资产流转模块使用单一 `Transfer` 模型，通过 `action_type` 字段区分不同操作类型（purchase/assign/return/transfer）。前端通过 `useTransferList(type)` composable 复用列表逻辑，每种类型对应一个 `*List.vue` 视图。

现有字段已覆盖：资产编号、资产名称、规格型号（对应"规格"）、调拨数量（对应"数量"）、备注、调出分公司（对应"分公司"）、调出部门（对应"所属部门"）、采购经办人（对应"经办人"）、调拨日期（对应"入库/出库日期"）。

用户要求的回收列表表头中，以下字段需要新增或映射：
- **序号** — 前端计算（行号）
- **分公司** — `调出分公司` 或 `from_branch`
- **资产编号** — 已有
- **资产类目** — 需关联 Category 或新增字段
- **物品分类** — 需关联 Category 或新增字段
- **资产名称** — 已有
- **回收分类** — 新增字段（如：报废回收、闲置回收、捐赠回收等）
- **入库日期** — `调拨日期`
- **数量** — `调拨数量`
- **单位** — 新增字段
- **规格** — `规格型号`
- **出库日期** — 新增字段
- **所属部门** — `调出部门`
- **当前处理状态** — `审批状态`
- **存放位置** — 新增字段
- **经办人** — `采购经办人`
- **备注** — 已有

## Goals / Non-Goals

**Goals:**
- 复用现有 Transfer 模型，新增 `recovery` action_type
- 新增回收专用字段：回收分类、单位、出库日期、存放位置
- 新增前端回收列表页，遵循现有 `*List.vue` 页面结构
- 回收列表表头按用户指定顺序显示

**Non-Goals:**
- 不重构现有 Transfer 模型架构
- 不实现回收审批流程（复用现有审批机制）
- 不实现回收分类的独立管理页面（使用简单 choice 字段）

## Decisions

### 1. 复用 Transfer 模型 vs 新建 Recovery 模型

**选择：复用 Transfer 模型**。理由：
- 现有 `action_type` 机制已支持多种操作类型
- 前端 composable `useTransferList(type)` 可直接复用
- 新增字段通过 migration 添加，所有 action_type 共享表结构（已有先例：`供应商`、`单价` 仅 purchase 使用）
- 避免 API、路由、序列化器的大面积重复

### 2. 新增字段方案

在 Transfer 模型上新增 4 个字段（均允许 blank/null，不影响现有数据）：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `回收分类` | CharField(max_length=50, blank=True) | 回收类型分类 |
| `单位` | CharField(max_length=20, blank=True) | 计量单位 |
| `出库日期` | DateField(null=True, blank=True) | 出库日期 |
| `存放位置` | CharField(max_length=200, blank=True) | 存放地点 |

### 3. 资产类目/物品分类映射

回收记录的"资产类目"和"物品分类"通过关联 Category 模型获取，或在 Transfer 上新增冗余字段存储。考虑到现有 Transfer 模型未关联 Category，**新增两个冗余字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `资产类目` | CharField(max_length=100, blank=True) | 如"固定资产类" |
| `物品分类` | CharField(max_length=100, blank=True) | 如"办公设备" |

### 4. 回收分类选项

回收分类使用固定 choice：
- 闲置回收
- 报废回收
- 捐赠回收
- 其他

## Risks / Trade-offs

- [Transfer 表字段持续增长] → 可接受的 trade-off，当前仅新增 6 个可选字段，不影响已有数据的存储和查询
- [回收列表部分字段与采购/调拨不相关] → 通过序列化器按 action_type 返回不同字段集，前端仅展示回收相关列
