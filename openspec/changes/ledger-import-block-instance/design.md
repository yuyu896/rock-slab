# 台账导入禁实例品目 — 技术设计

## Context

`AssetSummaryViewSet.import_excel`（差异预览/confirm 两阶段）经 `_parse_import_rows` 解析，行校验现有：资产编号在字典、分公司存在、数量格式。缺管理方式守卫。实例品目在库列=实例镜像（铁律 2：只能经单据变动），导入直改即账实分裂。

## Goals / Non-Goals

**Goals:** 行级拒绝实例品目（预览/confirm 双拦）；前端提示前置。

**Non-Goals:** 不动数量/消耗品导入；存量对账差异修复另案。

## Decisions

### D1：行级守卫与品目导入存量守卫同构

在 `_parse_import_rows` 品目命中后加：`if item.management_type == 'instance': errors.append(...); continue`。错误行不进 diffs → confirm 循环只遍历 diffs，两阶段一并拦截，无第二处改动。提示文案：`第 {i} 行: {asset_code} 为实例管理品目，不可台账导入（数量经采购入库单/流转单变动）`。

### D2：前端提示前置（轻量）

`SummaryImportDialog.vue` 的说明区补一句「实例管理品目不支持台账导入」，不新增校验逻辑（后端是硬约束）。

## Risks / Trade-offs

- [员工误以为品目错] → 错误文案明确指向管理方式而非编号错误
- [既有习惯被打破] → 数量/消耗品（绝大多数导入量）不受影响

## Migration Plan

随部署生效；无数据迁移。

## Open Questions

（无）
