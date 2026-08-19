## Context

固定资产表页面（FixedAssetList.vue）已有列表展示、搜索筛选、编辑/删除功能。后端 `FixedAssetViewSet` 已提供完整的 CRUD、import、export 端点。前端缺少导出、批量导入（含模板下载）、手动新增三个操作入口。

同项目的 RecoveryList.vue 已实现了完整的数据操作模式：页面头部三个按钮（导出 / 批量导入 / 新增）+ 对应的弹窗交互。本设计沿用相同模式，保持 UI 一致性。

## Goals / Non-Goals

**Goals:**
- 为固定资产表添加导出、批量导入、新增三个功能入口
- 交互流程与 RecoveryList.vue 保持一致
- 复用现有 API 端点和样式，最小化代码变更

**Non-Goals:**
- 不修改后端（端点已存在）
- 不改变已有的编辑/删除功能
- 不新增全局组件（复用弹窗模式即可）

## Decisions

1. **导出**：调用已有的 `exportAssets` API（`/api/assets/export`），但固定资产需使用专用端点 `/api/assets/fixed-assets/export`。如果后端未区分，则复用现有端点并传 `type=fixed` 参数。

2. **批量导入**：复用 FixedAssetList.vue 中已有的导入弹窗框架，增加模板下载步骤（与 RecoveryList.vue 一致的两步导入流程：下载模板 → 上传文件）。

3. **新增**：添加表单弹窗，字段参照后端 `FixedAssetSerializer` 的必填字段（资产编号、序列号等），使用 el-form 组件。

4. **按钮顺序**：导出 → 批量导入 → 新增（与 RecoveryList.vue 一致，新增按钮为 primary 样式在最右）。

## Risks / Trade-offs

- [后端导出端点可能不区分固定资产] → 先确认端点是否支持 `type` 参数，若不支持则前端直接调用通用导出，后续可扩展
- [新增表单字段较多] → 仅保留必要字段（资产编号必填），其余可选，降低用户填写成本
