# sidebar-navigation 增量

## ADDED Requirements

### Requirement: 工作台二维码右下角悬浮

「移动端安装」二维码卡片 SHALL 以 fixed 定位悬浮于视口右下角（right/bottom 各 20px），不占文档流——工作台指标卡与图表布局 MUST NOT 因其存在而变动。窄屏（<768px）SHALL 隐藏该卡片（不遮挡内容）。

#### Scenario: 右下角悬浮

- **WHEN** 用户打开工作台
- **THEN** 二维码卡片固定在页面右下角，指标卡/图表布局与无二维码时完全一致

#### Scenario: 窄屏隐藏

- **WHEN** 浏览器宽度 <768px
- **THEN** 二维码卡片不显示
