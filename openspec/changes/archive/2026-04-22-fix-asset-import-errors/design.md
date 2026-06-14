## Context

资产导入代码在 `assets/views.py` 的 `import_excel` 方法中，直接将 openpyxl 读取的原始值传给 `Asset.objects.create()`。Excel 数据的日期是整数序列号、布尔值是中文字符串、数字字段可能有 "/" 等无效值，全部会导致 Django ORM 报错，而错误信息是英文技术术语。

当前错误流程：openpyxl 读行 → 直接 create → 捕获 Exception → `errors.append(f'第 {i} 行: {str(e)}')` — 没有任何预处理和错误翻译。

## Goals / Non-Goals

**Goals:**
- 导入前对每行数据做类型预处理（日期、布尔、数字）
- UNIQUE 冲突时显示中文提示和具体的资产编号
- 字段验证错误时显示中文列名
- 同类错误合并显示，避免大量重复

**Non-Goals:**
- 不改导入的 Excel 模板格式
- 不增加行级事务（导入仍按行独立，一行失败不影响其他行）
- 不改前端的错误弹窗组件（后端返回格式保持 `{ imported, errors }`）

## Decisions

### 1. 提取公共导入工具函数

在 `utils/import_helpers.py` 中创建共享函数：日期转换、布尔转换、数字清理、错误翻译。资产/分类/流转导入共用。

**理由**: 三个 import_excel 有类似的问题，避免重复代码。

### 2. 导入前预处理而非导入后翻译

在传入 `create()` 之前，先对每个字段做类型转换和校验。校验失败直接生成中文错误信息，不抛到 ORM 层。

**理由**: 预处理可以给出精确到字段的错误提示（哪个列、什么值、期望什么格式），事后翻译很难从原始异常中提取这些信息。

### 3. 同类错误合并

用一个 `dict` 按「错误类型+错误信息」分组合并行号，输出时格式为 `第 3-26 行: 资产编号 A-a00011 已存在（共 24 行）`。

### 4. UNIQUE 冲突做特殊处理

在 create 之前先检查 `Asset.objects.filter(资产编号=code).exists()`，如果已存在则跳过 create 并记录友好的重复提示。

## Risks / Trade-offs

- **[预处理逻辑可能与 Django 验证重复]** → 预处理只做类型转换，不替代 Django 的字段验证（如 max_length）。Django 验证失败的错误仍需翻译。
- **[性能]** → 每行多一次 exists 查询，对几百行的导入影响可忽略。
