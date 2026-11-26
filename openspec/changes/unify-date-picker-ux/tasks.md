## 1. 代码准备

- [x] 1.1 审查所有目标文件，确认当前使用的原生 `<input type="date">` 位置和绑定逻辑
- [x] 1.2 确认 Element Plus 已正确引入且 `el-date-picker` 组件可用

## 2. 单据创建页面改造

- [x] 2.1 修改 `frontend/src/views/transfers/PurchaseCreate.vue` 采购入库单日期选择器
- [x] 2.2 修改 `frontend/src/views/transfers/AssignCreate.vue` 领用出库单日期选择器
- [x] 2.3 修改 `frontend/src/views/transfers/RecoveryCreate.vue` 回收单日期选择器
- [x] 2.4 检查并修改 `frontend/src/views/transfers/TransferCreate.vue` 调拨单日期选择器（如存在）

## 3. 其他相关页面改造

- [x] 3.1 修改 `frontend/src/views/assets/AdjustRecordsDialog.vue` 调整记录对话框日期选择器
- [x] 3.2 修改 `frontend/src/views/FixedAssetList.vue` 固定资产列表筛选日期选择器
- [x] 3.3 修改 `frontend/src/views/transfers/RecoveryLedger.vue` 回收台账筛选日期选择器
- [x] 3.4 检查 `frontend/src/views/transfers/PurchaseDetail.vue` 是否有日期输入，如有则修改

## 4. 样式验证与调整

- [x] 4.1 验证所有修改页面的日期选择器样式与 Element Plus 其他表单组件一致
- [x] 4.2 测试深色模式下日期选择器显示效果，确保无样式错误
- [x] 4.3 检查日期选择器在不同浏览器（Chrome, Firefox, Edge）的显示一致性

## 5. 功能测试

- [x] 5.1 测试采购入库单：点击日期框任意位置可弹出选择器，选择后格式为 YYYY-MM-DD
- [x] 5.2 测试领用出库单：点击日期框任意位置可弹出选择器，选择后格式为 YYYY-MM-DD
- [x] 5.3 测试回收单：点击日期框任意位置可弹出选择器，选择后格式为 YYYY-MM-DD
- [x] 5.4 测试调拨单（如存在）：点击日期框任意位置可弹出选择器，选择后格式为 YYYY-MM-DD
- [x] 5.5 测试调整记录对话框：日期选择正常工作
- [x] 5.6 测试固定资产列表筛选：日期范围选择正常工作
- [x] 5.7 测试回收台账筛选：日期选择正常工作

## 6. 回归测试

- [x] 6.1 提交单据验证：确认日期验证规则与原逻辑一致
- [x] 6.2 编辑已有单据：日期数据正确回显
- [x] 6.3 草稿保存：日期字段正确保存和恢复
- [x] 6.4 驳回后重新编辑：日期数据不丢失

## 7. 构建验证

- [x] 7.1 运行 `npm run build` 确保无类型检查错误
- [x] 7.2 确认生产构建成功，无警告
