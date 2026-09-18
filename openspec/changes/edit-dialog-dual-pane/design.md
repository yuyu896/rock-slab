# 编辑弹窗双栏 — 技术设计

## Context

编辑弹窗现单栏 520px（图片区 40px row-thumb）；生平是独立 el-drawer + 行按钮；编辑按钮沿用相机 svg。timeline 数据端点在位。

## Decisions

### D1：图标与操作列

编辑按钮 svg 换铅笔（M11 4H4... edit 曲线，项目其他处已有同款）；删除生平行按钮与 el-drawer（openTimeline 保留供编辑弹窗调用）——操作列两按钮。

### D2：双栏布局

弹窗 width 920px；body 用 grid `grid-template-columns: 1fr 1fr; gap: 16px`。左栏：现有 el-form（图片区改 `.edit-image-large`——预览 120px 高、图片行独立布局）。右栏：`edit-timeline` 容器 `max-height: 60vh; overflow-y: auto`——头部出生信息 + 流水表（迁移现 drawer 内容结构，样式压缩适配半栏）。openEdit 时并行调 getFixedAssetTimeline（loading 态），复用现有 timeline/timelineLoading refs。footer 保存按钮跨栏。

### D3：窄屏降级

`@media (max-width: 768px)` grid 改单列，两栏各自滚动。

## Risks / Trade-offs

- [右栏生平数据加载延迟] — 打开即并行拉取 + loading 态，不阻塞左栏编辑

## Migration Plan

随前端构建生效；**停本地不部署**。

## Open Questions

（无）
