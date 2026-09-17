# 提案：移动端扫码化改造——扫码优先、双引擎、连扫盘点

## Why

移动端现定位失焦：登录落地是仪表盘（待审批/今日操作等 PC 向信息），底部五 tab 里审批、资产浏览等对现场人员无用，找扫码功能要多点一步；摄像头识别仅依赖 BarcodeDetector，**iPhone Safari 与微信内置浏览器不可用**（公司 iPhone 众多），只能手动打字；盘点扫码每扫一台摄像头即关，无连扫模式，现场节奏被打断。

用户定稿移动端定位：**只做两件事——扫码盘点、日常扫码查询资产信息**，其余功能移出移动端（PC 保留）。

## What Changes

- **瘦身**：底部导航只留「扫码 / 盘点任务 / 我的」；登录落地页改为扫码页（`/mobile/home` 重定向 `/mobile/scan`）；工作台仪表盘、审批中心、资产浏览从移动端导航移除（页面路由保留不断链，PC 不受影响）
- **统一扫码器**（重写 `/mobile/scan`）：
  - 显式「开始扫码」入口（点击后才请求摄像头，避免落地即弹权限框），扫码会话内**常开连扫**（识别后不停机），同码 1 秒冷却防重复
  - **模式开关**：查询（默认）/ 盘点（存在进行中盘点任务时可选，支持 `?task=` 直达）
  - 查询模式：扫 QR 出资产卡片（内部编号/品目/状态/使用人/分公司），可跳完整详情
  - 盘点模式：扫 QR 精确匹配清单 → 自动打钩 → 震动+哔声反馈 → 继续扫；重复/清单外有明确提示
- **双引擎识别**：新增 `useBarcodeScanner` composable——有 BarcodeDetector 用原生（Android Chrome/Edge），否则 **jsQR** canvas 抓帧解码（iPhone Safari/微信可用）；两处旧摄像头代码（ScanAsset/MobileScan）收敛为一处
- **实例盘点入口统一**：任务列表「去盘点」按类型分流——实例盘跳扫码器（`?task=` 直达锁定任务），数量盘保留原任务页（逐项确认数量的交互不同，不并入本轮）；旧路由保留兼容深链
- 新增依赖：`jsqr`（~46KB，自带类型）

## Capabilities

### New Capabilities

- `mobile-scan-terminal`: 移动端扫码终端——统一扫码器（双引擎、连扫、查询/盘点双模式）与精简导航的移动端形态

### Modified Capabilities

（无——盘点/查询的业务规则不变，仅入口与交互形态变化）

## Impact

- 前端：`MobileLayout.vue`（导航瘦身）、`router`（落地重定向、旧页重定向）、重写 `mobile/ScanAsset.vue`（统一扫码器）、新增 `composables/useBarcodeScanner.ts`、`mobile/InventoryList.vue`（去盘点跳转）、退役 `MobileScan.vue`
- 依赖：+`jsqr`
- 后端：**零改动**（查询、checkInventoryInstance 均现成）
- 测试：composable 单测、扫码器页面测试、导航与重定向测试
