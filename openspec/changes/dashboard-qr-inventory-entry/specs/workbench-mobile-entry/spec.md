# workbench-mobile-entry 增量

## ADDED Requirements

### Requirement: 工作台二维码卡片文案如实描述盘点用途

工作台二维码卡片的文案 SHALL 以盘点为目的：标题为「移动端盘点」，主文案为「微信扫码使用移动端进行盘点」，提示行为「首次使用需登录，登录后选择盘点任务」。卡片文案 MUST NOT 出现安装话术（如「安装磐盘移动端」「安卓两下 · iPhone 四下」「装完桌面有图标」）。

#### Scenario: 打开工作台看到新文案

- **WHEN** 用户打开 PC 工作台
- **THEN** 二维码卡片显示标题「移动端盘点」、主文案「微信扫码使用移动端进行盘点」，不出现任何安装相关字样

### Requirement: 二维码指向移动端盘点入口

工作台二维码的内容 SHALL 为 `当前域名 + /mobile/inventory`（运行时按 location.origin 生成），扫码后进入移动端盘点任务列表；未登录时 SHALL 经登录页携带 `redirect=/mobile/inventory` 原路返回。

#### Scenario: 扫码进入盘点任务列表

- **WHEN** 已登录用户用手机扫工作台二维码
- **THEN** 手机浏览器打开 `<origin>/mobile/inventory`，落在盘点任务列表

#### Scenario: 未登录扫码后登录返回盘点入口

- **WHEN** 未登录（或 token 已失效）用户扫工作台二维码
- **THEN** 跳转登录页且地址含 `redirect=/mobile/inventory`，登录成功后落在盘点任务列表

### Requirement: 安装引导资产保留

本次变更 SHALL NOT 移除 `/install` 路由、InstallGuide 页面及 PWA 基础设施（manifest、主屏图标）；仅工作台二维码不再指向它们。

#### Scenario: 直接访问安装页仍可用

- **WHEN** 用户在浏览器直接输入 `<origin>/install`
- **THEN** 安装向导页正常渲染，行为与变更前一致
