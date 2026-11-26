## Why

当前单据创建页面使用原生 `<input type="date">` 组件，用户必须精确点击小的日历图标才能打开日期选择器。这个交互区域过小且不符合直觉，降低了表单填写效率。改用 Element Plus 的 `el-date-picker` 组件可以让整个输入框都可点击，提升用户体验并与系统其他日期选择器保持一致。

## What Changes

- 将所有单据创建/编辑页面的日期输入从原生 `<input type="date">` 替换为 `el-date-picker`
- 统一日期选择器的交互方式：点击输入框任意位置即可唤起日期选择器
- 保持现有的日期格式（YYYY-MM-DD）和验证逻辑不变
- 确保样式与 Element Plus 其他表单组件一致

## Capabilities

### New Capabilities
- `unified-date-picker`: 统一所有单据页面的日期选择器为 Element Plus 组件，提供一致的交互体验

### Modified Capabilities
<!-- 无现有功能的需求变更，仅为实现层面的 UI 组件升级 -->

## Impact

**前端文件:**
- `frontend/src/views/transfers/PurchaseCreate.vue` - 采购入库单
- `frontend/src/views/transfers/AssignCreate.vue` - 领用出库单
- `frontend/src/views/transfers/RecoveryCreate.vue` - 回收单
- `frontend/src/views/transfers/TransferCreate.vue` - 调拨单（如存在）
- `frontend/src/views/assets/AdjustRecordsDialog.vue` - 调整记录对话框
- `frontend/src/views/FixedAssetList.vue` - 固定资产列表（筛选用）
- `frontend/src/views/transfers/RecoveryLedger.vue` - 回收台账
- `frontend/src/views/transfers/PurchaseDetail.vue` - 采购详情

**用户影响:**
- 所有需要选择日期的单据操作交互更加便捷
- 视觉一致性提升（与 FilterPanel 等已使用 el-date-picker 的组件保持一致）

**无破坏性变更**，仅为 UI 组件升级，不影响数据格式或业务逻辑。
