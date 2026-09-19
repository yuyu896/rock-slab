# 二维码右下角 — 技术设计

## Decisions

### D1：fixed 定位角标

InstallQrCard 根元素改 `position: fixed; right: 20px; bottom: 20px; z-index: 100`（低于 Element 弹层层级但高于内容；弹窗默认 2000+，不冲突）。二维码 canvas 缩至 128px、卡片紧凑内边距。Dashboard.vue 删除 `.install-qr-slot` 包装与样式（模板里直接不渲染 slot div）。

### D2：窄屏隐藏

`@media (max-width: 768px) { .install-qr-card { display: none; } }`

## Migration Plan

随前端构建生效。

## Open Questions

（无）
