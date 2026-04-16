## Why

前端功能验证发现大量页面仅有 UI 外壳，核心业务逻辑未打通。资产流转 5 种操作（领用/归还/调拨/维修/报废）无创建表单，盘点全流程（创建→执行→提交→审批）均为占位符，资产详情页缺失，采购入库为空壳，严重影响系统可用性。需在 MVP 阶段将这些关键功能全部落地。

## What Changes

- **资产流转表单**：新增领用出库、归还、调拨、维修、报废 5 种单据的创建表单，每种均含资产选择、数量填写、审批提交，以及驳回操作
- **盘点全流程打通**：实现创建盘点任务（含漏盘/重复规则配置）、扫码/手动录入执行、提交审核、审批通过/驳回、驳回后重新盘点
- **资产详情页**：新增资产详情抽屉/面板，展示完整字段信息及流转历史
- **采购入库完善**：接入采购单列表 API、实现审批通过/驳回调用、模板导入/下载、草稿保存
- **资产标签码**：集成 JsBarcode 库生成 Code128 一维码，支持标签预览和打印
- **组织架构图**：新增树形层级可视化组件，展示集团-区域-分公司-人员关系
- **组织架构修复**：区域负责人下拉改为动态加载、新增启用/停用开关、修复搜索筛选逻辑、补充 admin/manager 角色选项
- **分类属性配置**：新增按分类动态配置属性字段的机制（如电子设备配 CPU/内存，家具配尺寸/材质）
- **Excel 模板导入**：实现分类导入和采购导入的文件上传、下载模板、导入结果反馈
- **Dashboard 角色视图**：根据用户角色动态过滤数据范围（全集团/区域/分公司）
- **统计报表修复**：填充分类分布图数据、月度趋势图数据，修复变动明细 Tab 数据源切换
- **移动端补全**：摄像头扫码（调用 getUserMedia）、通知列表页、单据提交表单、修改密码 UI
- **全局修复**：新增资产按钮绑定事件、导出功能实现、进度条快捷筛选按钮接入逻辑

## Capabilities

### New Capabilities

- `asset-transfer-forms`: 资产流转 5 种单据的创建表单与审批/驳回操作
- `inventory-workflow`: 盘点全流程（创建→执行→提交→审批→重新盘点）
- `asset-detail`: 资产详情页（抽屉面板 + 流转历史）
- `asset-barcode`: Code128 条码生成与标签打印
- `org-chart`: 组织架构树形可视化
- `category-attributes`: 分类动态属性配置机制
- `excel-import-export`: 分类与采购的 Excel 模板导入/下载
- `mobile-enhancements`: 移动端摄像头扫码、通知列表、单据提交、修改密码

### Modified Capabilities

## Impact

- **前端视图层**：修改 Transfer.vue、Inventory.vue、Purchase.vue、AssetList.vue、Category.vue、Organization.vue、Dashboard.vue、Reports.vue 等 10+ 个视图文件
- **前端 API 层**：需新增分类导入 API、报表趋势 API；现有 transfers/inventories API 已完备仅需在视图中引入
- **前端状态管理**：inventory store 需补全 create/start/check/submit/approve/reject 等 actions
- **新增依赖**：JsBarcode（条码生成）
- **后端**：需新增分类导入端点、报表分类/趋势端点（前端 API 已定义但后端可能缺失）
- **移动端**：新增 NotificationList.vue 页面及路由
