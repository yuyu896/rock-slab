## 1. 写入端脱敏

- [x] 1.1 `backend/apps/audit/utils.py` 新增 `mask_sensitive(data)` 纯函数：递归遍历 dict/list，`SENSITIVE_KEYS = {'password'}` 命中键值替换 `'***'`，剔除 `_state`
- [x] 1.2 `backend/apps/audit/decorators.py` 的 `before_data`（`__dict__` 序列化）与 `after_data`（响应序列化）两处接入 `mask_sensitive`

## 2. 存量清洗迁移

- [x] 2.1 新增 `apps/audit/migrations/0002_mask_sensitive_fields.py`：遍历 `before_data/after_data` 任一非空的行，用 `mask_sensitive` 清洗后 `save(update_fields=...)`，幂等
- [x] 2.2 验证：直接调用 0002 的 RunPython 函数本体断言清洗+幂等（SQLite 测试事务不支持反向迁移走完整 migrate 路径，接线为标准 RunPython，部署时自然执行）

## 3. 测试与收尾

- [x] 3.1 新增用例：更新用户后审计 `before_data['password'] == '***'` 且不含哈希前缀；`_state` 不在快照中；脱敏函数嵌套结构/幂等单测
- [x] 3.2 既有审计用例回归 + 全量 `pytest` 通过（870 passed / 5 skipped / 6 xfailed）
- [ ] 3.3 手验要点记录（审计页查看任一用户更新记录，beforeData.password 显示 ***）

> 手验要点：部署后（migrate 已自动清洗存量）以管理员登录 → 审计日志 → 找一条「更新用户」记录 → 详情里 beforeData 的 password 应显示 ***；历史记录同样如此。
