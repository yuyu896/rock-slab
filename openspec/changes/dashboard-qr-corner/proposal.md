# 工作台二维码移至右下角

## Why

「移动端安装」二维码卡片现在位于指标卡与图表之间的文档流中，占一行高度，挤占工作台原有布局。应为右下角悬浮常驻，不参与布局。

## What Changes

- InstallQrCard 改 `position: fixed; right: 20px; bottom: 20px`（z-index 高于内容、低于弹窗层），从文档流移出——工作台原有布局零变动
- 卡片形态微调为紧凑角标样式（缩小内边距/二维码 128px），鼠标悬停可加轻微浮起；窄屏（<768px）隐藏（避免挡内容）
- 移除 `.install-qr-slot` 包装（Dashboard.vue 模板与样式）
- 非目标：二维码内容（域名/install）与生成逻辑不动

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `sidebar-navigation`（工作台相关）：二维码卡片定位右下角悬浮

## Impact

- **前端**: 仅 Dashboard.vue（删 slot）与 InstallQrCard.vue（定位样式）
