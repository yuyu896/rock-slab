## Why

PC 端列表页的表格高度依赖魔法数字 `calc(100vh - 340px)`（资产明细/固定资产/资产汇总三页），其余列表页（四类流转单、类目、审计日志、盘点、采购）则整页跟随内容区滚动、分页被顶到页面文档流末尾。结果是：不同屏高下表格与分页位置不一致，矮屏出现双滚动条，高屏大量留白。总设计书（docs/design/asset-model-v2.md 第九节）将「列表页 flex 填充 + 分页钉底」列为小案①，作为后续台账主视图改造的布局地基。

## What Changes

- **MainLayout 内容区改纵向 flex 骨架**：`.main` 定高 100vh、`.content` 变 flex 列容器；非列表页行为不变（内容超高时仍由 `.content` 滚动）。
- **新增全局工具类 `.page-fill`**（styles/global.css）：列表页根节点声明「占满内容区高」，页内区块纵向排布，表格容器 `flex: 1` 内部滚动，分页 `flex-shrink: 0` 钉底。
- **替换魔法数字**：删除三处 `max-height: calc(100vh - 340px)`，表格高度完全由 flex 派生，任意屏高自适应。
- **表头 sticky 补齐**：表格改为内部滚动后，原先 `overflow: hidden` 容器内的表头（四类流转单、类目、盘点任务、审计日志、采购）补 `position: sticky`，滚动时表头常驻。
- **列表页默认每页 20 → 50**：BasePagination 默认值及各列表页初始 `pageSize`（含 useTransferList、Category 自定义每页条数选择器）统一为 50；后端 `max_page_size=100` 不需改动。
- **多视图页（盘点管理、采购入库）**：根节点仍占满内容区，非列表子视图（详情/新建）超高时页内滚动。

## Capabilities

### New Capabilities
- `list-page-flex-layout`: PC 端列表页纵向 flex 布局契约——页面占满内容区高、表格区域 flex:1 内部滚动且表头常驻、分页钉底；列表页默认每页 50 条。

### Modified Capabilities
<!-- 无：现有 specs 未对页面高度/滚动方式/默认每页条数立约。asset-summary spec 中「每页 20 条」仅为分页连续序号场景的示例参数，序号公式不变，无需改约。 -->

## Impact

- **前端布局骨架**：`layouts/MainLayout.vue`（.main/.content）、`styles/global.css`（.page-fill 工具类与内容区 flex 规则）。
- **列表页（根节点 .page-fill + 表格容器 flex + 表头 sticky）**：`views/AssetList.vue`、`views/FixedAssetList.vue`、`views/assets/AssetSummary.vue`、`views/transfers/{PurchaseList,AssignList,TransferList,RecoveryList}.vue`、`views/Category.vue`、`views/AuditLog.vue`、`views/Inventory.vue`（含 `views/inventory/InventoryTaskList.vue`）、`views/Purchase.vue`。
- **默认每页 50**：`components/BasePagination.vue`、`composables/useTransferList.ts`、上列各页初始 `pageSize`。
- **测试**：`src/tests/views/AssetSummary.test.ts` 中 pageSize:20 断言随默认值更新；无后端/接口/数据变更。
- **非目标**：Reports/Dashboard/Organization 页布局（组织页已有自管全高布局）、移动端页面、单据详情与新建页、后端分页默认值。
