## 1. 后端 — 公共导入工具

- [x] 1.1 新建 `utils/import_helpers.py`：`excel_date_to_python(val)` — Excel 序列号/字符串/ datetime 转 date
- [x] 1.2 `utils/import_helpers.py`：`parse_bool_cn(val)` — "是"/"否"/"true"/"false" 转 boolean
- [x] 1.3 `utils/import_helpers.py`：`parse_decimal_safe(val, field_name)` — 转换数字，无效值返回 (None, error_msg)
- [x] 1.4 `utils/import_helpers.py`：`merge_errors(errors)` — 同类错误合并，格式为「第 3-26 行: xxx（共 N 行）」

## 2. 后端 — 资产导入修复

- [x] 2.1 `assets/views.py` import_excel：使用 import_helpers 预处理日期、布尔、数字字段
- [x] 2.2 UNIQUE 冲突：create 前检查 exists，重复时记录友好错误
- [x] 2.3 Django 验证异常翻译：捕获 ValidationError/IntegrityError，转为中文提示
- [x] 2.4 使用 merge_errors 合并同类错误后返回

## 3. 测试

- [x] 3.1 单元测试：Excel 序列号 46057 正确转换为 date
- [x] 3.2 单元测试：布尔值 "否" 转为 False，"是" 转为 True
- [x] 3.3 单元测试：UNIQUE 冲突返回「资产编号 XXX 已存在」
- [x] 3.4 单元测试：数字字段 "/" 返回「不是有效数字」
