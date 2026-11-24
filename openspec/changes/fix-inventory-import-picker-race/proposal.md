## Why

生产环境的“导入盘点表”在用户选中文件后可能完全无响应。文件选择框打开后，零延时定时器会在文件尚未选中时清空任务 ID，导致后续 `change` 处理直接退出，确认框和导入请求均无法触发。该路径已通过隔离 Chromium 复现，生产静态资源也包含相同逻辑。

## What Changes

- 以文件选择、明确取消和导入完成事件管理导入状态，消除等待选择文件期间任务 ID 被提前清空的竞态。
- 保证用户停留在文件选择框后选中文件，仍能针对原任务进入确认和上传流程。
- 支持取消选择、取消确认、导入成功或失败后的再次操作，包括重新选择同一文件和切换到另一任务。
- 为确认和上传阶段设置重复操作保护，并为文件选择阶段配置适当的输入框与按钮状态。
- 增加真实等待顺序的回归验证，覆盖延迟选择文件、取消、同文件重选及任务绑定。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `frontend-contract-alignment` — 增加盘点结果导入的文件选择生命周期、任务绑定、取消恢复与重复提交保护要求。

## Impact

- `frontend/src/views/Inventory.vue` 的文件选择器事件、导入状态、确认流程和组件清理。
- `frontend/src/views/inventory/InventoryTaskList.vue` 的导入按钮状态联动，具体改动根据实现需要确定。
- `frontend/src/tests/views/BatchImportConfirmation.test.ts` 的文件选择等待、取消与再次导入用例。
- 使用现有 Vue、Element Plus 和 `importInventoryResult` 请求封装完成修复，并通过前端测试、构建和浏览器操作验证。
