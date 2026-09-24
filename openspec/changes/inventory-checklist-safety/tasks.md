## 1. 后端三重防护

- [x] 1.1 清单范围探测函数：与 `_generate_instance_items`/`_generate_items` 同源 queryset 抽公共条件（实例：在用×分公司×可选类目；台账：分公司×范围），返回计数
- [x] 1.2 `start`：can_transition 后先探测，为 0 → 400（文案见 spec）任务保持 pending；非空走原 transition+生成
- [x] 1.3 `download_template`：实例盘「核对结果」列 DataValidation 下拉（已找到/未找到，覆盖数据行区间）+「核对结果」「备注」表头 Comment；台账盘「实盘数量」表头 Comment
- [x] 1.4 `import_result`：清单空且有「不在盘点范围内」错误 → 响应附 `hint` 字段（病因+作废重建出路）

## 2. 前端

- [x] 2.1 `Inventory.vue` 导入结果处理：读 `result.hint`，有则 ElMessage.warning 展示（逐行错误展示逻辑照旧）

## 3. 测试与门禁

- [x] 3.1 后端测试：空范围 start 400（实例/台账两态、任务保持 pending）、非空照常进 in_progress、模板含下拉（load_workbook 校验 DataValidation）与批注、空清单导入响应含 hint、非空错行无 hint
- [x] 3.2 门禁：后端 pytest 全绿、前端 vitest 全绿、`npm run build` 通过

## 4. 收口

- [x] 4.1 拆两 commit（feat + openspec）并 push，等用户本地手验（空任务被拦、模板下拉、hint 展示）后自行部署
- [ ] 4.2 部署项：无迁移；上线抽查空范围开始被拦且文案清楚、模板打开见下拉
