## 1. 后端导入/导出 API

- [x] 1.1 在 TransferViewSet 中新增 `export_excel` action，输出包含表头的 Excel（流转记录模板）
- [x] 1.2 在 TransferViewSet 中新增 `import_excel` action，解析 Excel 逐行创建 Transfer 记录，支持中文 action_type 映射，返回 `{ imported, errors }`

## 2. 前端 API 方法

- [x] 2.1 在 `transfers.ts` 中新增 `importTransfers(file)` 方法
- [x] 2.2 在 `transfers.ts` 中新增 `exportTransfers()` 方法

## 3. 前端批量导入 UI

- [x] 3.1 在 Transfer.vue 操作栏添加"批量导入"按钮（导出与新建流转之间）
- [x] 3.2 新增批量导入弹窗状态变量和方法（showImportModal、importLoading、importResult、下载模板、上传、点击外部关闭）
- [x] 3.3 实现批量导入弹窗 HTML（三步式：下载模板 → 上传文件 → 查看结果）
- [x] 3.4 添加弹窗 CSS 样式

## 4. 收尾

- [ ] 4.1 验证完整流程：下载模板 → 填写数据 → 上传 → 查看结果
