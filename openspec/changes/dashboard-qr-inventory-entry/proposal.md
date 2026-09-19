# 工作台二维码改为移动端盘点入口

## Why

移动端的实际定位是**盘点终端**：员工拿手机到现场扫码盘点物资，替代纸笔逐个记录。但工作台二维码卡片的现行文案是「手机扫码，安装磐盘移动端 / 安卓两下 · iPhone 四下，装完桌面有图标」——承诺的是 PWA 安装，而手机实测（尤其微信内，iOS 微信无「在浏览器打开」入口）根本装不了。文案失实，员工按指引走不通。

## What Changes

- 二维码卡片文案改为以盘点为目的：「微信扫码使用移动端进行盘点」，删除所有安装话术（「安卓两下 · iPhone 四下」等）
- 二维码指向由 `/install`（安装向导页）改为 `/mobile/inventory`（盘点任务列表）：文案承诺盘点，扫码后应直接进入移动端盘点流程，而不是落在一个教人安装的页面上
- 登录链路已具备支撑：未登录会带 `?redirect=/mobile/inventory` 跳登录，登录后直达盘点任务列表（含今日已修的 401 死 token 回跳场景）
- `/install` 路由与 PWA 基础设施（manifest/图标）保留不动，只是不再由工作台二维码导流

## Capabilities

### New Capabilities

- `workbench-mobile-entry`: 工作台二维码卡片的入口语义——文案如实描述用途（微信扫码进移动端盘点）、二维码指向移动端盘点入口、不承诺安装动作。卡片定位/窄屏隐藏规则仍归 sidebar-navigation 管，本能力只管「入口是什么、指向哪、怎么说」。

### Modified Capabilities

（无——sidebar-navigation 中二维码卡片的定位规则不变，仅卡片内文案与链接目标变化，属本新能力的范畴）

## Impact

- `frontend/src/components/InstallQrCard.vue`：标题/主文案/提示行、二维码内容（`location.origin + '/mobile/inventory'`）
- `frontend/src/tests/components/InstallQrCard.test.ts`：断言新文案与新指向
- 不动：`/install` 路由、InstallGuide 页、PWA manifest/图标、MobileLayout 安装横幅（微信内 iOS 横幅文案失实是另一处类似问题，另行立项）
- 员工动线变化：微信扫码 → 登录（首次）→ 盘点任务列表 → 选任务进场盘点
