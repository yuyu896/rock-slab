# 任务：移动端扫码化改造

## 1. 基础设施

- [x] 1.1 `npm install jsqr`；新建 `composables/useBarcodeScanner.ts`：取流（后置摄像头）+ 双引擎识别（BarcodeDetector 优先 / jsQR canvas 降采样兜底）+ 400ms 轮询 + 同码 1000ms 冷却 + 卸载停流
- [x] 1.2 composable 单测：引擎选择、去抖逻辑、失败降级

## 2. 统一扫码器（重写 mobile/ScanAsset.vue）

- [x] 2.1 页面骨架：显式「开始扫码」入口（点击后请求摄像头并开始取景，权限弹窗不前置）+ 模式开关（查询默认/盘点可选）+ 手动输入兜底常显
- [x] 2.2 查询模式：扫码 → keyword 并行查台账+实例 → 资产卡片（内部编号/品目/状态/使用人/分公司）+ 查看详情跳转
- [x] 2.3 盘点模式：`?task=` 直达/切换锁定任务、清单匹配打钩（checkInventoryInstance）、震动+哔声反馈（Web Audio）、流水展示（已核对/重复/清单外）
- [x] 2.4 摄像头拒绝/失败提示与降级文案

## 3. 导航与路由

- [x] 3.1 `MobileLayout.vue` 底部导航瘦身为 扫码/盘点任务/我的
- [x] 3.2 路由：`/mobile/home` 重定向 `/mobile/scan`；`InventoryList.vue`「去盘点」按任务类型分流（instance → 扫码器 `?task=`，stock → 旧任务页，旧路由保留兼容深链）
- [x] 3.3 全局引用排查（MobileScan 旧引用清零）

## 4. 测试与验证

- [x] 4.1 页面测试：模式切换、查询卡片、盘点打链路（mock checkInventoryInstance）、重复与清单外提示、路由重定向
- [x] 4.2 `npm run test` 全量 + `npm run build`（类型门禁）
- [x] 4.3 浏览器实测：Android 引擎选择、连扫不停机、冷却去抖、查询/盘点双模式全流程、旧链接重定向（本地 dev）
- [ ] 4.4 真机验收：Android（Chrome）与 iPhone（Safari，借用户手机）摄像头扫码 + 微信内置浏览器打开——用户参与验收
