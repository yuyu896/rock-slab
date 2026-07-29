## 1. 品牌 logo 组件与资源

- [x] 1.1 新增 `frontend/src/components/BrandLogo.vue`：资产层叠 SVG（2-3 层堆叠盒 / 箱体轮廓 + 勾选点缀），支持 props：`size`、`variant`（`'mono'` 用 currentColor / `'brand'` 用 primary 渐变）、`hideText`（隐藏「磐盘」文字）。
- [x] 1.2 生成 `public/favicon.svg`（主）+ `public/favicon.png`（老浏览器回退）；确认小尺寸（~32px）下 logo 可辨，过于复杂则简化（去勾选）。

## 2. logo 全站应用

- [x] 2.1 `layouts/MainLayout.vue`：侧边栏顶部原通用立方体图标替换为 `<BrandLogo variant="mono" hideText />`（随侧边栏文字色）。
- [x] 2.2 `index.html`：favicon 引用 `/favicon.svg`（+ png 回退），加 `?v=2` 查询参数防浏览器强缓存。
- [x] 2.3 grep 全仓原立方体图标的 svg path，确认所有引用点已替换，无残留。

## 3. 登录页左右分栏

- [x] 3.1 重写 `frontend/src/views/Login.vue` 的 `<template>` 为左右分栏结构（左侧视觉区 + 右侧表单区）；**`<script setup>` 一行不改**。
- [x] 3.2 左侧容器：品牌蓝渐变背景（深色模式用 `primary-700/800`）+ `<BrandLogo variant="brand" />`（大号，主视觉）+ 「磐盘」标识 + 产品标语 + 轻量场景元素（少量资产 / 勾选小图标）。
- [x] 3.3 右侧表单：垂直居中、`max-width: 420px`，保留现有 logo / 标题 / 手机号 / 密码 / 显示密码 / 错误提示 / 登录按钮结构（可弱化卡片阴影）。
- [x] 3.4 CSS Grid 实现左右分栏；`@media (max-width: 960px)` 退化为单栏（隐藏左侧、表单全宽居中）。

## 4. 深色模式与令牌一致性

- [x] 4.1 所有新增颜色来自 `styles/variables.css` 令牌，无写死色值；logo（mono 版）随 `currentColor` 自适应深色模式。
- [x] 4.2 确认侧边栏 logo（~32px）、登录页 logo（大号）、favicon 三处显示正常、对比度可辨。
- [x] 4.3 若启用轻量动效，以 `@media (prefers-reduced-motion: reduce)` 守护禁用。

## 5. 验证

- [x] 5.1 `npm run build` 通过（vue-tsc 无类型错误）。
- [x] 5.2 `npm run dev` 目测：登录页宽屏 / 窄屏 / 深色模式、侧边栏 logo、浏览器 favicon。
- [x] 5.3 跑现有登录测试（`npm run test`）+ 手动登录（成功跳转 / 失败错误 / token 过期），确认逻辑未变。
- [x] 5.4 `openspec validate login-split-screen-layout` 通过。

## 6. 提交与部署

- [x] 6.1 拆两个 commit：`feat: 磐盘品牌 logo + 登录页左右分栏`（BrandLogo + Login + MainLayout + favicon）+ `chore(openspec): login-split-screen-layout 提案`。
- [x] 6.2 部署（前端 dist + favicon 由 nginx 服务，`deploy.sh` 或单独构建 + nginx reload；无后端 / DB 改动）。
- [x] 6.3 部署后提示：favicon 浏览器缓存激进，用户可能需硬刷新才看到新图标。
