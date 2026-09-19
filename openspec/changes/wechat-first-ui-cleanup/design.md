# 设计：移动端界面去失实元素

## Context

- 移动端定位 = 微信里直接用的盘点终端；工作台二维码已改指 `/mobile/inventory`（dashboard-qr-inventory-entry）
- 安装横幅（fc846c4）诞生于 PWA 推广期，iPhone 分支不看浏览器环境一律显示 Safari 指引——微信内做不到
- 盘点双形态：实例盘扫 FixedAsset 二维码（有码，入口在 ScanAsset 统一扫码器，微信可用）；数量盘按品目报数（**物资无码**），MobileScan 里的扫码入口无用
- MobileScan 兼职旧路由 `/mobile/scan/:taskId` 深链（实例盘打钩逻辑仍在，isInstanceTask 由任务 `inventoryKind` 判定）

## Goals / Non-Goals

**Goals:**

- 移动端任何页面不再出现安装引导横幅
- 数量盘任务页不出现扫码按钮与「不支持扫码」提示；实例盘（含旧路由深链）扫码不受影响

**Non-Goals:**

- 不删 `/install` 页与 PWA 资产（manifest/图标）：Chrome/Safari 用户仍可手动添加主屏
- 不给 MobileScan 的扫码接 jsQR 兜底改造：实例盘的微信路径已由 ScanAsset 承担，MobileScan 的扫码只服务旧路由深链，不值得投入
- 不动数量盘的手动输编号/搜索定位/报数交互（两种盘共用，现状可用）

## Decisions

1. **横幅整体删除，不做「微信内隐藏」的环境判断保留**——新方向下不再向员工推销安装；留环境判断等于留死代码。Chrome 用户想装仍可走浏览器菜单（manifest 完好）
2. **扫码 UI 按 `isInstanceTask` 条件渲染**（模板三处：camera-toggle-btn、camera-view、camera-not-supported 提示），而非删除代码——旧路由实例盘深链仍需要扫码，代码保留只对数量盘隐藏
3. **`toggleCamera` 加脚本层 `isInstanceTask` 守卫**——模板隐藏只是界面层，防 URL 直达/异常路径绕过
4. **手动输编号框不加条件**——数量盘靠它定位品目行，placeholder 已按任务类型区分

## Risks / Trade-offs

- [旧路由 `/mobile/scan/:taskId` 的实例盘深链在微信内仍扫不了（MobileScan 无 jsQR 兜底）] → 既有局限，本次明确不修；正常实例盘入口（任务列表 → ScanAsset）微信可用，深链存量极小
- [横幅删除后 Chrome 安装转化进一步降低] → 与新方向一致：不追求安装，追求微信即用
- [删横幅动 MobileLayout 的 import（onMounted/ref 可能失引用）] → build 类型门禁兜底
