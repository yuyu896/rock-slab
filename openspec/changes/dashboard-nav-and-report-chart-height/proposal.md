# 工作台待审批跳转修正 + 报表图表定高滚动

## Why

工作台「待审批」卡片点击跳 `/assets/transfer`（旧路由）→ 重定向到调拨列表——目标错误（待审批绝大多数是采购单）。统计报表图表卡片无高度上限，数据多长页面拖多长，观感差。

## What Changes

- 工作台待审批卡片跳转改为 **采购入库列表 + 自动套用「待审批」状态筛选**（`/transfers/purchase?status=待审批`；PurchaseList 支持从 route.query 初始化 status）
- 报表图表卡片定高（max-height 480px）：标题常驻，图表内容区（chart-body）内部滚动——页面长度恒定
- 非目标：不做统一"全部待审批"新页面（各类型列表已有状态筛选）；图表本身渲染逻辑不动

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `sidebar-navigation`（或工作台相关能力）：待审批快捷入口目标修正

## Impact

- **前端**: `Dashboard.vue`（跳转函数）、`PurchaseList.vue`（query 初始化 status）、`Reports.vue`（chart-card 定高 + chart-body 滚动）
