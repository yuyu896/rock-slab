## 1. 实现

- [x] 1.1 `inventories/views.py`：合并抽为模块级 `generate_task_checklist(task)`；start 的 `before_save` 内调用（事务内），删除事务外生成
- [x] 1.2 `check`/`check_instance`：`transaction.atomic` + 任务行 `select_for_update` 重取 + 锁内复查 in_progress；台账盘改查清单内 InventoryItem，缺行 404（删 get_or_create）
- [x] 1.3 `inventories/serializers.py`：CheckItemSerializer.qty 加 `min_value=0`
- [x] 1.4 `import_result` 台账盘分支：整数 float 接受、非整数/不可解析进 errors（删 int(float()) 截断）
- [x] 1.5 `inventories/models.py` 增 `INVENTORY_LOCKED_STATUSES` 与 `branch_inventory_locked()`；transfers `_check_inventory_lock`、inventories start 同分公司复查、assets 导入确认（聚合分公司名 400 INVENTORY_LOCKED）统一引用

## 2. 测试

- [x] 2.1 新增 `tests/test_inventory_checklist_integrity.py` 7 例：生成失败回滚（pending+0项+不锁分公司）、成功即生成、清单外 check 404 不建项、负数 qty 400、导入 2.9 报错/5.0 接受、导入确认盘点锁 400 且盘点完成后恢复
- [x] 2.2 存量 test_check_success 造数对齐真实 start（补清单生成+类目对齐）；全量 `pytest` 通过（895 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（负数/小数被拒；盘点期间导入确认被拦；正常盘点流程不受影响）

> 手验要点：盘点中提交负数实盘/导入含小数的 Excel 应被明确拒绝；开盘点期间对同分公司做台账导入确认应得「正在进行盘点」400；正常开始→核对→提交流程不受影响。
