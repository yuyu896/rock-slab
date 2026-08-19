## Context

资产列表页面（AssetList.vue）已有"导出"和"新增资产"按钮，后端已提供 `/api/assets/import`（POST，Excel 上传）和 `/api/assets/export`（GET，Excel 下载）接口。前端 `assets.ts` 中也已有 `importAssets()` 方法。当前缺少前端 UI 入口让用户使用批量导入功能。

## Goals / Non-Goals

**Goals:**
- 在资产列表页面操作栏新增"批量导入"按钮
- 弹窗支持下载导入模板、上传 Excel 文件、展示导入结果
- 导入完成后自动刷新资产列表

**Non-Goals:**
- 不修改后端 API
- 不实现导入预览/编辑功能（直接提交）
- 不实现断点续传或大文件分片上传

## Decisions

1. **复用现有 `importAssets()` API 方法** — `assets.ts` 已封装好，无需新增 API 代码
2. **模板下载复用 `exportAssets()` 导出空模板** — 后端 `/api/assets/export` 导出表头即为模板。但更优方案是新增一个专门的模板下载接口或直接用当前的 export 导出空数据。考虑到后端 export 已存在，先导出当前筛选条件的空 Excel 作为模板
3. **弹窗使用页面内自定义 Modal** — 与现有"新增资产"弹窗风格一致，不引入 Element Plus 的 el-dialog
4. **导入结果分成功/失败展示** — 成功数量用绿色高亮，失败明细逐条列出，便于用户定位问题行

## Risks / Trade-offs

- [大文件上传可能超时] → 设置 axios timeout 为 60s，并在上传时显示 loading 状态
- [Excel 格式不规范导致全部失败] → 展示后端返回的逐行错误信息，用户可修正后重新上传
