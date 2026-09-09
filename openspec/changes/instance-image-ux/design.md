# 实例图片 UX 修正 — 技术设计

## Context

图片功能（instance-image）上线后实测的两个问题，均为前端表现层：

1. `FixedAssetList.vue` 的 `.action-col { display: flex; gap: var(--space-1); }` 写在 `<td>` 上。CSS 表格布局中，`display: flex` 覆盖 UA 样式的 `table-cell`，使该单元格退出行布局：高度由内容（30px 按钮）决定，不随行高伸展，border-bottom 位置与同行其他单元格错开。历史行矮（纯文本行高 ≈ 按钮高）掩盖了这一点；图片列 40px 缩略图 + padding 把行撑到 ~64px 后暴露。
2. `uploadImage`/`handleDeleteImage` 成功分支只更新行数据与 `imagePreview`，弹窗（`imaging`）保持打开。

## Goals / Non-Goals

**Goals:**

- 挂图行内所有单元格分割线同高连续
- 上传/删除成功后弹窗自动关闭；失败停留

**Non-Goals:**

- 压缩行高（图片撑行是合理代价）
- 后端/接口/数据任何改动

## Decisions

### D1：td 恢复 table-cell，按钮行内排布

`.action-col` 去掉 `display: flex`，改 `white-space: nowrap`（防按钮换行）；`.action-btn` 由 `display: flex` 改 `display: inline-flex`（自身 30×30 定尺寸不变，按钮间用 `margin-right` 或父级字间距补 gap——取 `vertical-align: middle` 居中，间距 `margin-right: var(--space-1)`，末钮不留白不影响布局）。td 继承 `.data-table td` 的 `vertical-align: middle`，随行伸展，border-bottom 对齐。该类仅 FixedAssetList 使用，无全局外溢。

### D2：成功即关，失败停留

`uploadImage` 与 `handleDeleteImage` 的成功分支在更新行数据后置 `imaging.value = null`（复用 `imagingVisibleProxy` 的既有关闭路径，无新状态）。失败分支不动（catch 中仅提示，弹窗自然停留）。`imagePreview` 的同步更新保留在关闭前完成，无需额外清理。

## Risks / Trade-offs

- [inline-flex 在个别浏览器的基线缝隙] → `vertical-align: middle` 已定，实测以 `npm run build` + 手验为准
- [成功即关后批量补图需重开弹窗] → 每行单图，重开成本一次点击；且列表就地更新已确认结果

## Migration Plan

纯前端样式与交互微调，随下次 `deploy.sh` 前端构建生效；无数据、无回滚风险。

## Open Questions

（无）
