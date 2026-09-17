# 提案：移动端安装向导页 + PC 工作台安装二维码

## Why

移动端扫码终端与 PWA 基础设施已就绪（standalone、图标、安装横幅），但"员工怎么装上手机"仍靠口头教学：微信扫二维码打不开安装（需跳浏览器）、安卓找菜单、iPhone 找分享——分公司推广时每个员工都要教一遍。需要一个**自动化、分平台、图文一步到位**的安装引导，且分发入口成本要低到"行政在电脑上让员工扫一下屏幕"。

## What Changes

- **新增 `/install` 安装向导页**（公开页，无需登录、无移动端标签栏）：
  - 自动识别环境：微信内置浏览器 / 安卓 Chrome / 安卓厂商浏览器 / iPhone Safari，只显示当前环境需要的步骤
  - 微信内 → 第一步引导"右上角 ··· → 在浏览器打开"（配标注截图/示意图）
  - 安卓 Chrome → 大按钮【安装磐盘】联动 `beforeinstallprompt`（不触发则显示菜单图文步骤）
  - iPhone → 图文步骤"分享 → 添加到主屏幕"
  - 底部常驻【打开磐盘】按钮 → 直达 `/mobile/scan`（登录守卫自然接管）
- **PC 工作台（Dashboard）新增"移动端安装"卡片**：运行时用 `qrcode` 库生成二维码（内容 = `location.origin + '/install'`，生产/本地自适应）+ 一句话引导文案
- 路由：`/install` 顶层公开路由（与 `/login` 同级，`requiresAuth: false`）

## Capabilities

### New Capabilities

- `mobile-install-guide`: 移动端安装向导——分平台自动识别的图文安装引导页与 PC 端二维码分发入口

### Modified Capabilities

（无——不改动既有页面行为，Dashboard 仅新增卡片）

## Impact

- 前端：新增 `views/InstallGuide.vue`、路由项、`Dashboard.vue` 加卡片；复用现有 `qrcode` 依赖（运行时 toCanvas 生成）
- 零后端改动、零新依赖
- 测试：向导页环境识别与文案分支、Dashboard 卡片二维码渲染
