# 移动端界面去失实元素（微信直接用收口）

## Why

官方动线已定为「微信扫码直接用移动端」（dashboard-qr-inventory-entry），但移动端界面上还留着两处**与事实相悖的元素**：

1. **MobileLayout 页内安装横幅**：iPhone 上一律显示「iOS：Safari 分享 → 添加到主屏幕」——在微信里这个操作根本不存在，员工照做做不到；安卓 Chrome 的安装推销也不再是新方向想要的引导
2. **数量盘任务页的扫码入口**：数量管理的物资**没有二维码**（按品目记数量，无物可扫），摄像头按钮永远用不上，微信里还会弹出「当前浏览器不支持摄像头扫码」的误导提示

## What Changes

- 删除 MobileLayout 的安装横幅整体（模板 + `beforeinstallprompt` 捕获逻辑 + 样式 + sessionStorage 标记），不做环境判断式保留
- 数量盘任务页（MobileScan）按任务类型条件渲染扫码 UI：摄像头按钮、取景区、「不支持扫码」提示**仅实例盘任务（isInstanceTask）显示**；数量盘只剩搜索/手动输编号定位 + 报数
- `toggleCamera` 加脚本层守卫（数量盘任务直接返回），防 URL 直达绕过界面隐藏
- 保留：`/install` 页、PWA manifest/图标、实例盘（含旧路由深链）的扫码能力、手动输编号交互（两种盘共用）

## Capabilities

### New Capabilities

- `wechat-first-mobile-ui`: 微信直接用方向下的移动端界面如实性——不显示安装引导横幅；扫码入口仅出现在确有码可扫的场景（实例盘），数量盘界面只保留实际可用的定位与报数交互。

### Modified Capabilities

（无——横幅与数量盘扫码入口均无已确立的 spec 记录，属实现层移除 + 新立负面/条件性需求）

## Impact

- `frontend/src/layouts/MobileLayout.vue`：删横幅（script 10-36、template 71-77、CSS 99-102），顺带清理仅横幅使用的 `isIos`/`onMounted`/`ref` 引用
- `frontend/src/views/MobileScan.vue`：扫码 UI 三处加 `isInstanceTask` 条件 + `toggleCamera` 守卫
- 新增测试：MobileScan 数量盘/实例盘条件渲染；全量回归
- 不动：MobileScan 的扫码实现本身（BarcodeDetector-only 不为微信改造，实例盘微信路径已由 ScanAsset 统一扫码器承担）
