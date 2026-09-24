## 1. 单选统一

- [x] 1.1 `InstancePicker.vue`：删除 `single` prop 与多选分支（checkbox、「完成」按钮、多选已选计数文案），点选即 `update:modelValue=[id]`+`change` 并收起；触发文案统一「点选实例 / 已选 1 台」；跨行去重（excludedIds）保留
- [x] 1.2 `TransferLinesEditor.vue`：`:single="type === 'assign'"` 移除（组件恒单选）；`onInstancesChange` 置 `instances=[一台]`、`数量=1`；实例行校验断言保留
- [x] 1.3 收口：grep InstancePicker 消费方确认无多选 API 残留引用

## 2. 生平中文化与弹窗扩容

- [x] 2.1 `FixedAssetList.vue` 生平类型列：`TRANSFER_TYPES[row.actionType]?.label ?? row.actionType`
- [x] 2.2 行编辑弹窗 width 920px → 1160px

## 3. 测试与门禁

- [x] 3.1 前端测试：点选即定收起与换选；一行一台数量自动 1；跨行去重；生平类型中文渲染（assign→领用出库、未知值兜底）
- [x] 3.2 门禁：前端 vitest 全绿、`npm run build` 通过（后端零改动不跑全量，常规抽查即可）

## 4. 收口

- [x] 4.1 拆两 commit（feat + openspec）并 push，等用户本地手验（四类创建页点选 + 生平弹窗）后自行部署
- [ ] 4.2 部署项：纯前端无迁移；上线抽查四类建单点选与生平中文
