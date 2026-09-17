# 任务：移动端安装向导页 + PC 工作台二维码

## 1. 向导页（views/InstallGuide.vue）

- [x] 1.1 页面骨架：极简页头（磐盘/标语）+ 环境自适应步骤区 + 底部「打开磐盘」常驻按钮（跳 `/mobile/scan`）
- [x] 1.2 环境识别：微信（UA MicroMessenger）/ iPhone（UA）/ 安卓三分支；安卓侧 `beforeinstallprompt` 触发则出【安装磐盘】大按钮（preventDefault 后手动 prompt），300ms 未触发回退菜单图文步骤
- [x] 1.3 微信分支：右上角 ··· → 在浏览器打开 引导（图标+文字示意，截图素材后补）

## 2. 路由与 PC 入口

- [x] 2.1 路由：顶层公开路由 `/install`（与 `/login` 同级，`requiresAuth: false`，title 安装磐盘）
- [x] 2.2 `Dashboard.vue` 新增"移动端安装"卡片：`qrcode.toCanvas` 运行时生成二维码（内容 `location.origin + '/install'`，180×180 含白边）+ 引导文案（安卓两下 · iPhone 四下）

## 3. 测试与验证

- [x] 3.1 向导页测试：UA 三分支渲染断言（微信/iPhone/安卓文案）、安装按钮 prompt 联动（mock beforeinstallprompt）、「打开磐盘」跳转
- [x] 3.2 Dashboard 卡片测试：二维码 canvas 渲染、卡片文案
- [x] 3.3 `npm run test` 全量 + `npm run build`（类型门禁）
- [x] 3.4 浏览器实测：未登录直达 /install、UA 模拟三分支、Dashboard 二维码扫码实链路（本地扫进向导页）、微信内打开引导正确（本地 dev）
