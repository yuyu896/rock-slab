# 品目页筛选与序号 — 设计

## Context

品目页（`frontend/src/views/Category.vue`）现有筛选：关键词、资产类目、物品分类，均透传后端分页接口（`/api/categories/`，`CategoryFilterSet` 执行，中文参数名惯例：`资产类目`/`物品分类`/`keyword`）。表格视图 11 列无序号；卡片视图无序号。台账页（AssetSummary.vue）已确立分页连续序号惯例：`(pagination.page - 1) * pagination.pageSize + index + 1`，并有 vitest 断言防回归。

导出按钮现状只透传 资产类目+关键词（漏物品分类），`export-filter-alignment` 规格第 42-43 行把该现状固化成了需求。

## Goals / Non-Goals

**Goals:**
- 管理方式筛选：前端下拉（全部/数量管理/实例管理/消耗品）→ 后端过滤参数 → 分页结果随之收窄
- 序号列：表格首列分页连续序号，卡片视图序号角标，与台账页同公式
- 导出参数补齐：资产类目+物品分类+管理方式+关键词 全量透传

**Non-Goals:**
- 不改 Category 模型/序列化/权限/导入导出模板
- 不做管理方式批量迁移入口（已有 `migrate_consumables` 命令）
- 卡片视图不加筛选以外的改版

## Decisions

1. **筛选参数名沿用中文惯例**：`CategoryFilterSet` 增 `管理方式 = CharFilter(field_name='management_type')`，与既有 `资产类目`/`物品分类` 参数风格一致（前端直接发中文名，djangorestframework-camel-case 不涉及该层）。选项值为枚举 `quantity/instance/consumable`，非法值自然空结果（django-filter 精确匹配），无需额外校验。
2. **筛选选项硬编码三档**：下拉选项直接映射 `MANAGEMENT_TYPE_LABELS`（constants 已与后端枚举对齐），不从全量数据派生——管理方式是封闭枚举，派生反而会出现"缺某档时选项消失"的怪表现。
3. **序号纯前端计算**：`(page-1) × pageSize + index + 1`，不新增后端字段。与 AssetSummary 完全同公式，翻页连续（第 2 页从 51 起）。卡片视图同公式取 `index + 1`（卡片不分页？——卡片同样用分页数据源 `filteredCategories`，故用同公式）。
4. **导出参数对齐不做条件拼装**：导出调用直接传当前四个筛选 ref（空值 undefined 不发），与 fetchCategories 同源，杜绝再次漏参。

## Risks / Trade-offs

- [筛选值拼写不一致导致空结果] → 选项 value 固定用枚举键（quantity/instance/consumable），与模型 choices 同源；后端精确匹配，测试覆盖三档各命中
- [序号列挤压表格宽度] → 序号列窄列样式（复用台账页 `col-index` 风格），11 列变 12 列在现有自适应下可容纳；必要时品目名列已有备注折行不受影响
- [导出行为变化] → 原"只带类目+关键词"是漏参缺陷，补齐后导出结果更贴合用户所见，属规格修正（export-filter-alignment 增量同步）

## Migration Plan

纯表现层与查询参数，无迁移、无数据变动。部署走常规 deploy.sh；回滚即代码回滚。
