## Why

草稿状态半死：后端 draft 创建能力现成（`draft=true` 存为草稿，通知层已过滤仅待审批才发），但**前端全站无任何入口能存草稿**；撤回到草稿后需再点一次「修改」才进编辑，流程有断点；列表统计卡无草稿数，草稿存在感为零。

## What Changes

- 创建页操作区双按钮：**「提交审批」**（现状）+ **「存为草稿」**（带 `draft: true` 调既有创建接口）
- 撤回成功后**自动进入编辑态**（复用既有 `startEdit('draft')`，确认弹窗已防误触）
- 采购列表统计卡新增**「草稿」**（前端 computed，与现有待审批/已通过同口径）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `purchase-warehousing`: 新增三组需求（ADDED）：创建页存为草稿入口、撤回后自动进入编辑、列表草稿统计卡

## Impact

- 前端：`PurchaseCreate.vue`（+按钮）、`PurchaseDetail.vue`（撤回成功后调 startEdit）、`useTransferList.ts`（stats 增 draft 字段）+ `PurchaseList.vue`（统计卡）
- 后端：**零改动**——draft 创建路径、状态机、通知过滤（signals 仅 `待审批` 发通知，已核实 signals.py:81）均有既有测试覆盖
- 防误伤边界：不碰状态机/守卫/台账；草稿建单通知不发（既有过滤）；统计卡为前端页内计算无接口变更
