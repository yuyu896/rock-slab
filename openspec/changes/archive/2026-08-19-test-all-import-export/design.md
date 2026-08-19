## Context

项目有 7 个业务模块涉及 Excel 导入/导出操作，共 22 个后端端点。当前后端已有部分导入导出测试（`test_import_helpers.py`），但覆盖面不完整——缺少对资产导出、分类导入/导出、调拨 4 种类型的模板下载/导入/导出、盘点导入等的系统性覆盖。

近期代码变更引入了潜在回归风险：
- `TransferActionSerializer` 补全了 13 个字段（recovery/purchase 独有字段）
- 新增了 `recovery` 类型的导入模板（前端 `importTemplate.ts`）
- trailing slash 统一修复可能影响 import/export 的 URL 路由

### 现有测试资产

| 文件 | 覆盖范围 | 缺失 |
|------|---------|------|
| `tests/test_import_helpers.py` | 资产导入（基础 CRUD）、导入 helper 函数 | 资产导出、分类导入/导出、调拨导入/导出、盘点导入、模板下载 |
| `tests/test_transfers.py` | 调拨 CRUD + 审批流程 | 批量导入/导出端点未测试 |
| `tests/test_inventories.py` | 盘点 CRUD + 状态流程 | 导入模板/结果端点未测试 |

## Goals / Non-Goals

**Goals:**
- 为全部 22 个导入/导出/模板端点编写自动化后端测试
- 每个端点覆盖：正常流程 + 常见错误场景
- 重点验证字段完整性（尤其是最近补全的 recovery/purchase 字段不会在导入中丢失）
- 验证模板表头与导入解析逻辑的一致性
- 验证导出数据的列顺序和字段值正确性

**Non-Goals:**
- 不修改任何业务代码
- 不编写前端测试（vitest）——仅后端 pytest
- 不测试文件编码/字符集问题（openpyxl 统一处理）
- 不测试并发导入/导出的竞态条件
- 不测试性能/大文件压力（>10MB）

## Decisions

### 1. 测试文件组织：单文件 vs 多文件

**决策**：新建 `backend/tests/test_import_export.py` 单文件，约 60-80 个测试用例。

**理由**：
- 导入/导出逻辑跨多个模块但测试模式高度统一（构造 Excel → 上传/下载 → 断言），放在一个文件便于共享 helper 函数
- 现有 `test_import_helpers.py` 已验证 helper 层，新文件专注端点级别的集成测试
- 如果后续用例超过 150 个再考虑拆分

**备选方案**：每个模块一个文件（`test_asset_import_export.py`、`test_transfer_import_export.py` 等）——增加文件数但无实际收益，且 helper 函数需跨文件共享。

### 2. 测试数据构造方式

**决策**：使用 `openpyxl` 在内存中构造 Excel 文件（`io.BytesIO`），不依赖磁盘文件。

**理由**：
- 避免测试数据文件的管理和路径问题
- 内存构造速度快，适合 CI 环境
- 与现有 `test_import_helpers.py` 中的 `_make_xlsx` 模式一致

### 3. 模板验证策略

**决策**：对每个模板下载端点，验证：
1. HTTP 200 + Excel Content-Type
2. openpyxl 可解析
3. 第一行表头与该模块导入解析所需的列名完全匹配

**理由**：模板和导入解析是最容易不同步的地方。通过断言表头列名确保模板下载和导入解析使用相同的列定义。

### 4. 导出验证策略

**决策**：对每个导出端点，先创建测试数据，调用导出，验证：
1. HTTP 200 + Excel Content-Type
2. 数据行数与创建的记录数匹配
3. 随机抽检 2-3 条记录的关键字段值

**理由**：完整字段对比维护成本高且脆弱，关键字段抽检能覆盖 80% 的回归问题。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 导入解析逻辑硬编码了列索引，列顺序变更可能导致字段错位 | 模板下载测试会验证表头列名，与导入解析的列顺序不一致时测试会失败 |
| recovery 类型导入是新增功能，可能存在未发现的边界问题 | 对 recovery 类型做更细致的字段完整性断言，逐一验证所有新增字段 |
| SQLite 开发环境与 PostgreSQL 生产环境的 Excel 处理行为可能不同 | 导入/导出逻辑不涉及数据库特性差异，风险低 |
