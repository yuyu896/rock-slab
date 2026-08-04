## Why

磐盘是面向中国企业的固定资产管理系统，已上线 qhpanpan.top。当前**缺少专门的品牌 logo**——各处（侧边栏顶部、浏览器 favicon、登录页）都用一个通用立方体线条图标，品牌识别度弱；登录页是居中卡片式，视觉单薄。作为企业系统的「门面」，应当有专属品牌标识 + 更专业的登录入口。

本次做两件事：(1) 设计磐盘专属品牌 **logo**（资产层叠概念），**全站统一应用**；(2) 登录页改为**左右分栏**，左侧以 logo + 品牌标识为主，右侧登录表单。在不改登录流程的前提下，显著提升品牌识别度与专业感。

## What Changes

### A. 品牌 logo 设计 + 全站应用
- **设计 logo**：采用「**资产层叠**」概念——堆叠的资产盒 / 箱体轮廓，体现固定资产的存储与管理。SVG 矢量，线条 / 几何扁平风格，与系统现有图标一致，用 `currentColor` + 设计令牌着色（支持深色模式）。
- **全站统一应用**：浏览器 **favicon**、**PC 侧边栏顶部**（MainLayout）、**登录页**左侧——统一替换原通用立方体图标，保证品牌一致。
- logo 提供单色版（随主题变色）+ 固定品牌色版，适配深 / 浅背景。

### B. 登录页左右分栏
- 宽屏（≥960px）：左侧**品牌视觉区**（logo + 磐盘标识 + 产品标语 + 轻量场景元素）+ 右侧**登录表单**，各占约 50%。
- 窄屏（<960px）：退化为单栏，登录表单全宽居中，左侧视觉隐藏。
- 深色模式自适应；复用 `styles/variables.css` 设计令牌。
- **登录逻辑（手机号 + 密码、token、校验、跳转、错误提示）零改动**。

## Capabilities

### New Capabilities

- `brand-logo`: 磐盘品牌 logo（资产层叠 SVG）+ 全站统一应用（favicon / 侧边栏 / 登录页），深色模式自适应。
- `login-split-screen-layout`: 登录页左右分栏布局——左侧品牌视觉区（logo 为主）+ 右侧登录表单；窄屏单栏表单优先；登录逻辑不变。

### Modified Capabilities

（无。logo 与登录页布局此前均无独立 spec。）

## Impact

- **新增**：logo SVG（作为 Vue 组件 `BrandLogo.vue` 便于复用 + 静态 favicon 文件）。
- **前端代码**：
  - `views/Login.vue`（重写 `<template>` / `<style>`，`<script setup>` 不动）
  - `layouts/MainLayout.vue`（侧边栏顶部图标替换为 BrandLogo）
  - `index.html` / public 下 favicon 替换
- **设计令牌**：复用 `styles/variables.css`，不新增变量。
- **后端 / API / 数据库**：无任何改动。
- **风险**：logo 全站替换需确认各处（favicon 缓存、侧边栏尺寸、登录页）显示正常；登录逻辑不动，功能零风险。
