## Why

供应商在采购明细行为自由文本，同一供应商被录成多种写法（"华为"/"华为技术"/"华为技术有限公司"），数据碎片化：无法按供应商汇总、无法查历史交易、无法做价格参考。各分公司供应商高度重合且量少（用户确认），应与品目/部门同为**全集团扁平字典**。

## What Changes

- 新增 `Supplier` 模型（全集团扁平，无分公司维度）：名称（全局唯一）、联系人、电话
- 新增 `/api/suppliers` 接口：**读**（列表/选项）登录即可；**写**（增删改）仅系统管理员
- 前端管理页：侧边栏 组织架构 → 部门字典 → **供应商字典**（`/suppliers`，admin 可见，照 DepartmentManage 朴素表格形态）
- 采购行编辑器「供应商」列：自由文本输入改为**下拉选择**（选项来自字典，只准选不准手输）
- 明细行存储不变：`TransferLine.供应商` 仍存名称文本（记录性快照，同「创建人」模式）——存量老单显示零影响，不做数据归一

## Capabilities

### New Capabilities

- `supplier-dictionary`: 供应商扁平字典的模型、管理接口与权限、表单选择消费

### Modified Capabilities

（无——purchase-warehousing 的表单交互变化在 supplier-dictionary 需求中以场景覆盖）

## Impact

- 后端：新增 `apps/suppliers/` app（模型/序列化器/ViewSet/urls，镜像既有小 app 结构）；一条 migration（纯建表）
- 前端：`api/suppliers.ts`、`views/SupplierManage.vue`、路由+侧边栏一项、`TransferLinesEditor.vue` 供应商单元格改下拉
- **零影响区（防误伤核心）**：Transfer/TransferLine 模型不动；**API 层不做供应商强校验**——流转导入流（Excel）的供应商文本路径原样保留，避免导入被字典卡死；报表不动（按供应商统计另行立项）
- 存量数据：不迁移不归一，老单文本照旧展示
