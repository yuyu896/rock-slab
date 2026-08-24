# fixed-asset-import Specification（修改）

## REMOVED Requirements

### Requirement: Import button in header
**Reason**: Excel 导入即绕过单据直写实例，违反实例层铁律；存量实例由本迁移承载，新增走采购单。
**Migration**: 「批量导入」按钮移除；存量迁移后无需导入路径（如 P3 出现期初实例批量诉求，另立提案）。

### Requirement: Import dialog with two steps
**Reason**: 同上，导入流程整体下线（含 fa 模板校验/序号生成/去重系列行为一并废止）。
**Migration**: 导入端点返回 410；模板下载端点下线；前端导入弹窗移除。
