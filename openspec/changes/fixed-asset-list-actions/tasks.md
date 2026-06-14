## 1. 前端 API 层

- [x] 1.1 在 `assets.ts` 中新增 `exportFixedAssets` 导出函数，调用 `/api/assets/fixed-assets/export` 端点
- [x] 1.2 在 `assets.ts` 中新增 `createFixedAsset` 创建函数，POST 到 `/api/assets/fixed-assets`

## 2. 页面头部按钮

- [x] 2.1 在 FixedAssetList.vue 的 `header-actions` 区域添加"导出"按钮（btn-secondary 样式，含下载图标）
- [x] 2.2 在"导出"按钮后添加"批量导入"按钮（btn-secondary 样式，含上传图标），权限控制 `v-if="canManageAssets"`
- [x] 2.3 在最右侧添加"新增"按钮（btn-primary 样式，含加号图标），权限控制 `v-if="canManageAssets"`

## 3. 导出功能

- [x] 3.1 实现 `handleExport` 方法，调用 `exportFixedAssets` 传入当前筛选参数，处理 Blob 下载
- [x] 3.2 添加导出加载状态和错误提示

## 4. 批量导入功能（两步弹窗）

- [x] 4.1 重构现有导入弹窗为两步流程：步骤1 下载模板 + 步骤2 上传文件，与 RecoveryList.vue 一致
- [x] 4.2 实现 `handleDownloadTemplate` 方法，下载固定资产导入模板
- [x] 4.3 更新 `handleImport` 方法，显示导入结果（成功条数 + 错误列表）

## 5. 新增功能（表单弹窗）

- [x] 5.1 添加新增弹窗状态（showCreateModal、creating、form）
- [x] 5.2 实现 `openCreateModal` 方法，重置表单并打开弹窗
- [x] 5.3 实现 `submitCreate` 方法，表单验证（资产编号、资产名称必填）+ 调用 `createFixedAsset` API
- [x] 5.4 添加新增弹窗模板（el-dialog + el-form），字段包括：资产编号（必填）、资产名称（必填）、序列号、供应商、使用人、所属部门、当前状态（下拉）、分公司（下拉）、备注
