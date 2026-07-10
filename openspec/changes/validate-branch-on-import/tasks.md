## 1. 公共助手：分公司名称集合

- [x] 1.1 新增 `apps/organizations/utils.py`：`get_branch_name_set()`（返回名称集合）+ `branch_validation_error(name, label, valid_names)`（空→「为空，请填写」；非空不存在→「「X」不存在」；通过返回 None）

## 2. 资产导入校验

- [x] 2.1 `apps/assets/views.py` 资产 `import_excel`：导入开始预加载分公司名称集合；逐行将「分公司」`.strip()` 后校验——为空 → `分公司为空，请填写`；非空但不在集合 → `分公司「{name}」不存在`；任一不通过则 `raw_errors.append((行号, msg))` 并 `continue`（create 改用 trim 后的名称）
- [x] 2.2 新增用例：不存在分公司行 → 被拒并报错；空分公司行 → 被拒并报错

## 3. 流转导入校验

- [x] 3.1 `apps/transfers/views.py` 流转 `import_excel`：预加载集合；按 `type` 校验 `调出分公司`、以及 transfer 的 `调入分公司`——为空 → `调出/调入分公司为空`；非空但不存在 → `调出/调入分公司「X」不存在`；任一不通过则按既有 errors 格式报错并跳过
- [x] 3.2 新增用例：transfer 类型 调出分公司不存在/为空 → 被拒并报错；并修正既有流转/资产导入测试（补建所引用的分公司）

## 4. 验证

- [x] 4.1 后端 `pytest` 全绿（348 passed）
- [ ] 4.2 本地手动验证：导入含不存在/空分公司的 Excel，确认该行被拒且提示明确
