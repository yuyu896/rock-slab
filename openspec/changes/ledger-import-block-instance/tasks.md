# 台账导入禁实例品目 — 实施任务

## 1. 后端守卫

- [x] 1.1 `_parse_import_rows` 品目命中后加 `management_type == 'instance'` 行级拒绝（计入 errors 跳过，不进 diffs）
- [x] 1.2 后端测试：实例品目行预览/confirm 双拦（无 diff、无调整单、errors 含提示）；数量/消耗品行不受影响

## 2. 前端提示

- [x] 2.1 `SummaryImportDialog.vue` 说明区补「实例管理品目不支持台账导入」提示

## 3. 验证

- [x] 3.1 全量 pytest；`npm run build` + vitest 全绿
- [x] 3.2 本地手验：导入含实例品目的文件 → 预览报行级错误且不产生该行差异
