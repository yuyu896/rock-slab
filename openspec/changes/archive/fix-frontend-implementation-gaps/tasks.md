## 1. 组织架构模块修复

- [x] 1.1 Organization.vue：区域编辑表单的"区域负责人"下拉改为动态加载 `GET /api/users?role=supervisor`，替换硬编码选项
- [x] 1.2 Organization.vue：区域、分公司、用户列表新增 `el-switch` 启用/停用状态切换控件，切换后调用对应 update API
- [x] 1.3 Organization.vue：修复关键词搜索筛选逻辑，对区域/分公司/用户列表应用 computed 过滤
- [x] 1.4 Organization.vue：修复区域下拉筛选，对分公司和用户列表按选中区域过滤
- [x] 1.5 Organization.vue：用户角色下拉补充 admin 和 manager 选项（从 ROLE_LABELS 常量中获取）
- [x] 1.6 新增组织架构树形可视化组件（Vue 递归组件 + CSS Flexbox），渲染 集团→区域→分公司→人员 层级，展示角色标签和人数统计
- [x] 1.7 Organization.vue 新增"架构图"视图 Tab，集成树形可视化组件

## 2. 资产分类属性配置

- [x] 2.1 Category.vue 编辑表单新增"属性模板"配置区域，支持添加/删除动态属性（属性名、类型、是否必填、下拉选项）
- [x] 2.2 属性模板数据保存到分类的扩展字段中（利用现有 remarks 或新增前端本地 schema 字段）
- [x] 2.3 AssetList.vue 新增资产表单：根据选中分类的属性模板动态渲染额外属性输入框
- [x] 2.4 资产详情抽屉中展示分类动态属性值

## 3. 资产详情与新增

- [x] 3.1 AssetList.vue：实现资产详情 `el-drawer` 右侧抽屉，展示所有资产字段（基本信息、位置、数量价值、日期、图片、备注）
- [x] 3.2 资产详情抽屉新增"流转历史"区域，调用 `GET /api/transfers?assetCode=xxx` 展示该资产流转记录
- [x] 3.3 AssetList.vue："新增资产"按钮绑定点击事件，打开新增表单弹窗（el-dialog），包含分公司、资产编号、分类、名称、数量等必填字段
- [x] 3.4 新增资产表单提交调用 `createAsset` API，成功后刷新列表

## 4. 资产标签码生成与打印

- [x] 4.1 安装 JsBarcode 依赖（`npm install jsbarcode`）
- [x] 4.2 新增 `utils/barcode.ts` 工具函数，封装 Code128 条码生成逻辑（渲染到 SVG/Canvas）
- [x] 4.3 AssetList.vue：单个"打印标签"按钮打开标签预览弹窗，展示条码+资产信息
- [x] 4.4 批量"打印标签"按钮支持多资产生成标签预览
- [x] 4.5 标签预览弹窗"打印"按钮调用 `window.print()`，配合 CSS `@media print` 仅打印标签区域

## 5. 资产流转表单（核心）

- [x] 5.1 Transfer.vue：新增 Tab 页签切换（全部/领用出库/归还/调拨/维修/报废），按类型筛选列表数据
- [x] 5.2 Transfer.vue：新增"领用出库"创建表单弹窗（资产编号选择、数量、领用人、部门、日期、备注），提交调用 `assignAsset` API
- [x] 5.3 Transfer.vue：新增"归还"创建表单弹窗（资产编号、归还数量、日期、备注），提交调用 `returnAsset` API
- [x] 5.4 Transfer.vue：新增"调拨"创建表单弹窗（资产编号、调出/调入分公司和部门、数量、原因、负责人），含校验（调出调入不能相同），提交调用 `transferAsset` API
- [x] 5.5 Transfer.vue：新增"维修"创建表单弹窗（资产编号、维修原因、数量、备注），提交调用 `repairAsset` API
- [x] 5.6 Transfer.vue：新增"报废"创建表单弹窗（资产编号、报废原因、数量、备注），提交调用 `scrapAsset` API
- [x] 5.7 Transfer.vue：列表每行和操作栏新增"驳回"按钮，点击弹出输入驳回原因对话框，确认后调用 `rejectTransfer` API
- [x] 5.8 Transfer.vue：实现流转详情 `el-dialog` 弹窗，展示单据完整字段（类型、审批状态、审批人、时间等）
- [x] 5.9 Transfer.vue：实现导出功能，将当前筛选的流转记录导出为 Excel

## 6. 采购入库完善

- [x] 6.1 新增 `api/purchases.ts`（或在现有 API 中补充），定义采购单列表获取 API
- [x] 6.2 Purchase.vue：`purchaseOrders` 列表接入 API 获取，页面加载时 fetch 采购单数据
- [x] 6.3 Purchase.vue：审批通过按钮调用 `approveTransfer` API 替换空壳 `ElMessage`
- [x] 6.4 Purchase.vue：新增驳回操作，输入驳回原因后调用 `rejectTransfer` API
- [x] 6.5 Purchase.vue："下载模板"按钮实现下载 Excel 模板文件
- [x] 6.6 Purchase.vue："确认导入"按钮绑定 `handleImport` 逻辑，调用 `importAssets` API 上传文件并显示结果
- [x] 6.7 Purchase.vue："保存草稿"按钮绑定事件，调用 API 保存草稿状态

## 7. 盘点全流程打通（核心）

- [x] 7.1 Inventory.vue：创建盘点任务表单（任务名称、分公司、分类、漏盘规则、重复盘点规则），调用 `createInventoryTask` API
- [x] 7.2 Inventory.vue：删除盘点任务按钮，调用后端 destroy API
- [x] 7.3 Inventory.vue："作废"按钮调用 `cancelInventory` API
- [x] 7.4 Inventory.vue：审批通过按钮绑定 `@click` 事件，调用 `approveInventory` API
- [x] 7.5 Inventory.vue：新增驳回按钮和原因对话框，调用 `rejectInventory` API
- [x] 7.6 Inventory.vue："重新盘点"按钮改为调用 `recountInventory` API（替代当前错误的 `startInventory` 调用）
- [x] 7.7 Inventory.vue：盘点报告按钮调用 `getInventoryReport` API，展示差异明细、盘盈盘亏统计、未盘点清单
- [x] 7.8 MobileScan.vue：扫码输入框绑定事件，输入资产编号后查询资产，弹出确认对话框
- [x] 7.9 MobileScan.vue：确认对话框中输入实际数量后调用 `checkInventoryItem` API 提交盘点记录
- [x] 7.10 MobileScan.vue：提交审核按钮绑定 `@click` 事件，调用 `submitInventory` API
- [x] 7.11 MobileScan.vue：完成盘点按钮调用 API 完成盘点流程，替换当前仅弹消息的逻辑
- [x] 7.12 MobileScan.vue：进入扫描视图时调用 `getInventoryProgress` API 获取实时进度
- [x] 7.13 MobileScan.vue：调用 `getInventoryChecks` API 展示各盘点人的操作记录（多人协作）
- [x] 7.14 inventory store：补全 createTask / startTask / checkItem / submitTask / approveTask / rejectTask / recountTask / cancelTask / fetchProgress / fetchReport / fetchChecks actions

## 8. Dashboard 与报表修复

- [x] 8.1 Dashboard.vue：根据用户角色传递 scope 参数（admin/manager 无 scope，supervisor 传 regionId，leader/staff 传 branchId）给统计 API
- [x] 8.2 Reports.vue：调用报表 API 获取分类维度统计数据，填充 `categoryStats` 和环形图
- [x] 8.3 Reports.vue：获取月度趋势数据填充 `monthlyTrend` 和柱状图（需后端配合或从 transfers API 聚合）
- [x] 8.4 Reports.vue：修复"变动明细"Tab 切换后数据源改为调用 `getTransferReport` API
- [x] 8.5 Reports.vue：导出按钮实现 Excel 导出功能

## 9. Excel 导入导出

- [x] 9.1 Category.vue：实现"下载模板"按钮，下载分类导入 Excel 模板
- [x] 9.2 Category.vue：实现分类 Excel 导入功能（文件上传 + 调用 `POST /api/categories/import` + 结果展示），需后端新增端点
- [x] 9.3 分类导入 API：前端 `api/categories.ts` 新增 `importCategories` 函数

## 10. 移动端增强

- [x] 10.1 ScanAsset.vue / MobileScan.vue：新增摄像头扫码功能（`getUserMedia` + `BarcodeDetector`），不支持时降级为手动输入
- [x] 10.2 新增 `views/mobile/NotificationList.vue` 页面，调用通知 API 展示通知列表，支持标记已读
- [x] 10.3 新增 `/mobile/notifications` 路由，在 MobileLayout 底部导航或 Profile 中添加入口
- [x] 10.4 Home.vue"提交入库"快捷入口跳转到移动端采购入库表单页（新增或复用组件）
- [x] 10.5 Profile.vue：新增修改密码功能（旧密码 + 新密码 + 确认密码表单），调用 `updatePassword` API
- [x] 10.6 Profile.vue：通知未读数改为从 `notificationStore.unreadCount` 动态读取，替换硬编码的 3

## 11. 其他修复

- [x] 11.1 AssetList.vue：快速筛选按钮（库存不足/待维修/本月新增）绑定实际筛选逻辑
- [x] 11.2 各页面 `el-message` 占位符统一替换为真实 API 调用或移除
- [x] 11.3 全局：审查所有按钮事件绑定，确保无遗漏的空壳按钮
