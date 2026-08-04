# frontend-contract-alignment Specification

## Purpose
TBD - created by archiving change audit-findings-remediation. Update Purpose after archive.
## Requirements
### Requirement: 前端 API 调用必须使用规范化的封装与正确 URL 前缀

前端所有后端调用 MUST 经 `api/*.ts` 的封装函数（统一走 `utils/request.ts` 实例），不得在 store / view 中直接拼接根路径或绕过实例使用原生 `fetch`。URL MUST 带 `/api` 前缀以命中代理与反代规则。

#### Scenario: 删除盘点任务请求真实命中后端
- **WHEN** 用户在盘点列表点击 pending 任务的"删除"
- **THEN** 前端经 `deleteInventoryTask(id)` 发起 `DELETE /api/inventories/{id}`，后端收到请求并删除，列表刷新

### Requirement: 盘点报告字段必须与后端序列化器对齐

盘点报告 MUST 能正确展示每条盘点项的资产编号与资产名称。后端 `InventoryItemSerializer` MUST 暴露 `asset_code` 与 `asset_name`（来源 `asset.资产编号` / `asset.资产名称`）；前端 MUST 渲染这两个字段。

#### Scenario: 盘点报告资产编号/名称非空
- **WHEN** 用户打开一个已完成盘点的报告
- **THEN** 表格"资产编号""资产名称"两列展示对应资产的真实值，不空白

### Requirement: 资产详情的流转历史必须按资产过滤

资产详情抽屉 MUST 仅展示当前资产的流转历史。后端 MUST 提供按资产编号过滤流转的查询参数；前端 MUST 传入当前资产的标识进行过滤。

#### Scenario: 资产详情仅展示该资产的流转
- **WHEN** 用户点击某资产的"详情"
- **THEN** 抽屉"流转历史"仅列出涉及该资产编号的流转单，不混入其他资产的流转

### Requirement: 移动端盘点分公司字段必须正确读取

移动端扫码盘点页 MUST 正确读取任务的分公司字段（与后端序列化器字段名一致），不得因字段名错配导致分公司恒空。

#### Scenario: 手机端显示任务所属分公司
- **WHEN** 用户在手机端进入某盘点任务的扫码页
- **THEN** 顶部正确显示该任务所属分公司名称

### Requirement: 前端死代码与无效入口必须清理

无引用且字段错配的组件（如 `ImportDialog.vue`）、绕过拦截器的原生 `fetch` 封装（如 `categories.exportCategories`）、后端忽略的死参数（如 `Dashboard.buildScopeParams`）MUST 被移除或改为走统一封装；不存在的路由入口（如 PC 端 `/notifications`）MUST 补路由或移除入口。

#### Scenario: 导出分类走统一请求实例
- **WHEN** 用户导出分类
- **THEN** 请求经 `request` 实例发起，401/400 时用户得到正确提示，错误响应不被误当文件下载

