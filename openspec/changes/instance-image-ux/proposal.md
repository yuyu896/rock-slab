# 实例图片 UX 修正——行分割线对齐 + 弹窗成功即关

## Why

图片功能上线后的两个实测体验问题：

1. **行分割线错位**：挂图行变高后，操作列单元格与数据单元格的下边框（行分割线）不齐。根因是 `.action-col { display: flex }` 直接写在 `<td>` 上——`display: flex` 覆盖了表格单元格的 `table-cell` 布局，该 td 高度退化为内容高（30px 按钮），不随行高伸展；此前行矮不明显，图片列把行撑到 ~64px 后肉眼可见。
2. **弹窗不自动关**：上传/删除成功后弹窗仍停留，需要再点一次关闭。每实例仅单图，操作成功即完成，停留只多一步点击。

## What Changes

- 操作列 `<td>` 恢复表格布局：去掉 `display: flex`，按钮改行内排布（`white-space: nowrap` + 按钮 `inline-flex` + 间距），行内所有单元格 border-bottom 恢复同高对齐；垂直居中沿用既有 `vertical-align: middle`
- 图片弹窗：上传成功与删除成功后**自动关闭**（删除已有确认框兜底），列表缩略图就地更新与成功提示不变
- 非目标：不压缩行高（图片缩略图 40px 撑起的行高是合理代价）；不改后端

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fixed-asset-table-columns`: 新增两条要求——实例行全部单元格分割线同高对齐（任何 td 不得用非表格 display 破坏行布局）；图片弹窗上传/删除成功后自动关闭

## Impact

- **前端**: 仅 `views/FixedAssetList.vue`（`.action-col`/`.action-btn` 样式 + `uploadImage`/`handleDeleteImage` 成功分支补关闭）与其测试
- 后端、API、数据均不动
