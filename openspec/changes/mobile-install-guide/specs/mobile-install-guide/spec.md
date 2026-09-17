# mobile-install-guide Specification

## Purpose
移动端安装向导：分平台自动识别的图文安装引导页（/install 公开页）与 PC 工作台二维码分发入口，让员工扫码后按引导完成"添加到主屏幕"，无需人工教学。

## ADDED Requirements

### Requirement: 安装向导页公开可达
系统 SHALL 提供无需登录的 `/install` 页面，作为移动端安装引导的唯一入口地址。

#### Scenario: 未登录访问向导页
- **WHEN** 未登录用户访问 `/install`
- **THEN** 页面正常展示安装引导（不跳转登录页）

#### Scenario: 打开磐盘入口
- **WHEN** 用户点击向导页的「打开磐盘」
- **THEN** 跳转 `/mobile/scan`，未登录时由登录守卫接管

### Requirement: 环境自适应引导
向导页 SHALL 自动识别运行环境（微信内置浏览器 / iPhone / 安卓），并仅展示当前环境所需的安装步骤。

#### Scenario: 微信内打开
- **WHEN** 在微信内置浏览器中打开向导页
- **THEN** 步骤区显示"右上角 ··· → 在浏览器打开"的引导，不显示安装按钮

#### Scenario: 安卓 Chrome 且可安装
- **WHEN** 在支持安装的安卓 Chrome 中打开向导页且安装横幅事件可触发
- **THEN** 显示【安装磐盘】按钮，点击后弹出系统安装确认框

#### Scenario: 安卓浏览器不可自动安装
- **WHEN** 安卓浏览器未触发安装横幅事件（如厂商浏览器）
- **THEN** 显示"浏览器菜单 → 添加到主屏幕"的图文步骤兜底

#### Scenario: iPhone 打开
- **WHEN** 在 iPhone 浏览器中打开向导页
- **THEN** 显示"分享 → 添加到主屏幕 → 添加"图文步骤

### Requirement: PC 工作台安装二维码
PC 工作台 SHALL 展示"移动端安装"卡片，内含指向 `/install` 的实时生成二维码。

#### Scenario: 二维码内容自适应
- **WHEN** 工作台页面渲染安装卡片
- **THEN** 二维码由前端运行时生成，内容为 `当前站点域名/install`（本地与生产各自正确）

#### Scenario: 卡片引导文案
- **WHEN** 用户查看安装卡片
- **THEN** 展示"手机扫码，安装磐盘"引导语及安卓/iPhone 步数提示
