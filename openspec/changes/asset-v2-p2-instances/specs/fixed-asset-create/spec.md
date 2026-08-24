# fixed-asset-create Specification（修改）

## REMOVED Requirements

### Requirement: Create button in header
**Reason**: 手动创建实例冻结——实例出生 = 采购单（或存量迁移），防止绕过单据制造台账/实例漂移（铁律 2 的实例版）。
**Migration**: 页头「新增」按钮移除；新增实例改走采购入库单（实例管理品目行生效时自动生成）。

### Requirement: Create form dialog
**Reason**: 同上，创建入口整体下线。
**Migration**: 前端新增弹窗与 FixedAssetCreate 页面/路由/导航入口移除；后端 POST /api/fixed-assets/ 返回 405 并提示经流转单操作。
