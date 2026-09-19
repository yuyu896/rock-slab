# 任务：移动端界面去失实元素

## 1. 删除安装横幅

- [x] 1.1 MobileLayout.vue：删除横幅模板、`beforeinstallprompt` 捕获与 `showInstallBanner`/`dismissBanner`/`doInstall`/`dismissed`/`isIos` 逻辑、`.install-banner` 系样式；清理仅横幅使用的 `onMounted`/`ref` import

## 2. 数量盘扫码入口条件化

- [x] 2.1 MobileScan.vue：摄像头按钮（camera-toggle-btn）、取景区（camera-view）、「不支持扫码」提示（camera-not-supported）三处模板加 `isInstanceTask` 条件
- [x] 2.2 MobileScan.vue：`toggleCamera`/`startCamera` 加 `isInstanceTask` 脚本层守卫；手动输编号框不动

## 3. 测试与验收

- [x] 3.1 新增 MobileScan 条件渲染测试（mock 任务接口）：数量盘任务不渲染扫码按钮与不支持提示、实例盘任务照常渲染
- [x] 3.2 全量 vitest 通过 + npm run build（类型门禁）通过
- [ ] 3.3 手验收口：微信打开移动端确认顶部无横幅；微信进数量盘任务确认无扫码入口且输编号定位正常；旧路由实例盘深链扫码不受影响
