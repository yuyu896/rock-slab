# 实例盘点 Excel 模板与导入 — 技术设计

## Context

`download_template`（views.py:607）与 `import_result`（views.py:653）对实例盘任务 400 拦截；前端 InventoryTaskList 两个按钮对实例盘不渲染。台账盘的模板=品目数量行（资产编号/账面/实盘），实例盘清单是实例行（内部编号/使用人），列形态不同，需各自分支。

## Goals / Non-Goals

**Goals:** 实例盘模板下载（清单快照）+ 结果导入（matched/missing 回写），护栏与台账盘一致。

**Non-Goals:** 不改点选/扫码；不引入序列号导入匹配（模板主键=内部编号，序列号仅展示）；漏盘规则/差异处置不动。

## Decisions

### D1：同端点双分支，模板主键=内部编号

`download_template` 与 `import_result` 内按 `task.is_instance_inventory` 分流（替换原 400 拦截）。实例模板列：序号/内部编号/序列号/品目编号/品目名称/使用人/所属部门/核对结果/备注；导入按「内部编号」列匹配 `task.instance_items`（内部编号唯一，序列号可能待补录不作键）。

### D2：导入结果映射与既有核对同口径

「已找到」→result='matched'，「未找到」→result='missing'；`check_count += 1`、`checked_by/checked_at` 写操作人；备注列非空则写入 remarks。空结果列行跳过（未盘项不动，漏盘规则提交时处理）。行级错误（非法值/不在清单）收集返回，不中断。

### D3：前端只动按钮显隐

去掉两个按钮的 `v-if="task.inventoryKind !== 'instance'"`（下载/导入既有事件链路对实例盘天然可用——后端分流后响应一致）。

## Risks / Trade-offs

- [导入覆盖点选结果] → 与「重复核对以最后一次为准」一致（check_count 累加），预期行为
- [模板被改内部编号导致匹配失败] → 行级错误提示「不在盘点范围」，不中断

## Migration Plan

纯逻辑分支，无迁移；随部署生效。

## Open Questions

（无）
