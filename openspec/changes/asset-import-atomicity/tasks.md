## 1. 实现

- [x] 1.1 `backend/apps/assets/services/ledger.py` 新增 `apply_import_adjustments(entries, operator)`：整体 atomic + 按 (branch,item) 序锁齐（与 apply_document 全局序一致）+ 锁内复核现值==快照（IMPORT_STALE 带行号定位）+ 逐行 `_apply_delta` 与调整单留痕，返回 applied
- [x] 1.2 `backend/apps/assets/views.py` 的 confirm 分支替换为调用新入口（删除逐行 apply_adjustment 循环）

## 2. 测试

- [x] 2.1 新增 `tests/test_asset_import_atomicity.py` 4 例：行2 联动为负整体回滚（无调整单残留）；请求内解析→应用窗口注入并发变动 → IMPORT_STALE 且台账保持并发值（mock 确定性复现）；正常确认 applied=2；同文件二次确认幂等（applied=0 无二次变动）
- [x] 2.2 既有导入/台账契约/架构守卫回归 + 全量 `pytest` 通过（888 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（同文件二次确认应得「请重新上传」类提示且台账不变）

> 手验要点：上传导入文件预览差异 → 确认入账 → **原样再传一次并确认**：应 applied=0、台账与调整单数量不变；期间若有他方改台账，确认应得「台账现值已变化…请重新上传」400。
