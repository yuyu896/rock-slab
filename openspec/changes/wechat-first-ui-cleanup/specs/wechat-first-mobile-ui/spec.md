# wechat-first-mobile-ui 增量

## ADDED Requirements

### Requirement: 移动端不显示安装引导横幅

移动端所有页面 SHALL NOT 显示 PWA 安装引导横幅，SHALL NOT 捕获/响应 `beforeinstallprompt` 做页内推销。`/install` 向导页与 PWA manifest/图标资产 MUST 保留（浏览器菜单手动安装路径不受影响）。

#### Scenario: 移动端页面顶部无横幅

- **WHEN** 用户在任意浏览器（含微信、iPhone Safari、安卓 Chrome）打开移动端任意页面
- **THEN** 页面顶部不出现安装引导横幅，正文直接从页面内容开始

#### Scenario: 手动安装路径仍可用

- **WHEN** 安卓 Chrome 用户通过浏览器菜单选择「安装应用/添加到主屏幕」
- **THEN** 依据 manifest 正常完成添加（PWA 资产未变）

### Requirement: 扫码入口仅限实例盘任务

数量盘任务页 SHALL NOT 显示摄像头扫码按钮、取景区与「浏览器不支持扫码」类提示；这些扫码 UI SHALL 仅在实例盘任务（`inventoryKind=instance`，含旧路由深链）中显示。数量盘的搜索/手动输编号定位品目与报数交互 MUST 保持不变，且扫码启动函数 MUST 在数量盘任务下拒绝启动（防 URL 直达绕过）。

#### Scenario: 数量盘任务无扫码入口

- **WHEN** 用户打开数量盘任务（inventoryKind 非 instance）
- **THEN** 页面不出现扫码按钮与「不支持扫码」提示，仅保留编号输入定位与报数交互

#### Scenario: 实例盘任务扫码入口保留

- **WHEN** 用户通过旧路由深链打开实例盘任务（inventoryKind=instance）
- **THEN** 扫码按钮照常显示可用（行为与变更前一致）

#### Scenario: 数量盘下扫码函数拒绝启动

- **WHEN** 数量盘任务中通过任何途径触发摄像头启动
- **THEN** 不发起摄像头调用，界面无取景区
