# 提案：全面测试所有导入/导出功能

## Why

项目中有 7 个模块共涉及 **导入、导出、模板下载** 三类 Excel 操作，共计 **21 个功能端点**。这些功能是日常业务的高频操作（批量数据录入、数据备份、报表输出），一旦出现模板列不匹配、导入静默丢数据、导出文件损坏、中文乱码等问题，会直接影响业务运转。

近期多次修改涉及：Transfer 序列化器字段补全、recovery 模板新增、trailing slash 统一、导入列顺序调整等。这些变更可能引入回归问题，需要对所有导入/导出入口进行系统性测试，确保：

1. 模板下载 → 得到带正确表头的空 Excel 文件
2. 批量导入 → 按模板填写后上传，数据正确入库、字段无丢失
3. 导出 → 下载的 Excel 包含完整数据、列顺序与列表页一致
4. 边界情况 → 空文件、错误格式、超大文件、特殊字符等不会导致服务崩溃

## What Changes

编写自动化测试用例覆盖以下 7 个模块的 21 个功能点，分为后端 pytest 测试和前端手工验证清单。

### 功能点矩阵

| # | 模块 | 功能 | 后端端点 | 前端入口 | 测试类型 |
|---|------|------|---------|---------|---------|
| **资产模块 (Asset)** |
| 1 | Asset | 模板下载 | `GET /api/assets/template` | AssetImportDialog | 自动化 |
| 2 | Asset | 批量导入 | `POST /api/assets/import` | AssetImportDialog | 自动化 |
| 3 | Asset | 导出 | `GET /api/assets/export` | AssetList 导出按钮 | 自动化 |
| **固定资产模块 (FixedAsset)** |
| 4 | FixedAsset | 模板下载 | `GET /api/assets/fixed-assets/template` | FixedAssetList | 自动化 |
| 5 | FixedAsset | 批量导入 | `POST /api/assets/fixed-assets/import` | FixedAssetList | 自动化 |
| **分类模块 (Category)** |
| 6 | Category | 模板下载 | `GET /api/categories/template` | CategoryImportDialog | 自动化 |
| 7 | Category | 批量导入 | `POST /api/categories/import` | CategoryImportDialog | 自动化 |
| 8 | Category | 导出 | `GET /api/categories/export` | Category 导出按钮 | 自动化 |
| **调拨模块 — 采购 (Transfer/purchase)** |
| 9 | Transfer | 模板下载 | `GET /api/transfers/template?type=purchase` | PurchaseList 模板按钮 | 自动化 |
| 10 | Transfer | 批量导入 | `POST /api/transfers/import?type=purchase` | PurchaseList 导入弹窗 | 自动化 |
| 11 | Transfer | 导出 | `GET /api/transfers/export?type=purchase` | PurchaseList 导出按钮 | 自动化 |
| **调拨模块 — 领用 (Transfer/assign)** |
| 12 | Transfer | 模板下载 | `GET /api/transfers/template?type=assign` | AssignList 模板按钮 | 自动化 |
| 13 | Transfer | 批量导入 | `POST /api/transfers/import?type=assign` | AssignList 导入弹窗 | 自动化 |
| 14 | Transfer | 导出 | `GET /api/transfers/export?type=assign` | AssignList 导出按钮 | 自动化 |
| **调拨模块 — 调拨 (Transfer/transfer)** |
| 15 | Transfer | 模板下载 | `GET /api/transfers/template?type=transfer` | TransferList 模板按钮 | 自动化 |
| 16 | Transfer | 批量导入 | `POST /api/transfers/import?type=transfer` | TransferList 导入弹窗 | 自动化 |
| 17 | Transfer | 导出 | `GET /api/transfers/export?type=transfer` | TransferList 导出按钮 | 自动化 |
| **调拨模块 — 回收 (Transfer/recovery)** |
| 18 | Transfer | 模板下载 | `GET /api/transfers/template?type=recovery` | RecoveryList 模板按钮 | 自动化 |
| 19 | Transfer | 批量导入 | `POST /api/transfers/import?type=recovery` | RecoveryList 导入弹窗 | 自动化 |
| 20 | Transfer | 导出 | `GET /api/transfers/export?type=recovery` | RecoveryList 导出按钮 | 自动化 |
| **盘点模块 (Inventory)** |
| 21 | Inventory | 模板下载 | `GET /api/inventories/{id}/import-template` | Inventory 页面 | 自动化 |
| 22 | Inventory | 批量导入 | `POST /api/inventories/{id}/import-result` | Inventory 页面 | 自动化 |

### 测试用例设计

每个功能点覆盖以下场景：

**模板下载测试：**
- 返回 200 状态码
- Content-Type 为 Excel 格式
- 文件非空且可被 openpyxl 解析
- 表头行包含预期列名（与导入解析逻辑一致）

**批量导入测试：**
- 正常数据导入成功，返回 `{ imported: N, errors: [] }`
- 数据库中可查到导入的记录，所有字段值正确（重点验证最近补全的 recovery 字段：`回收分类`、`单位`、`出库日期`、`存放位置`、`资产类目`、`物品分类`）
- 空文件返回明确错误信息
- 错误格式文件返回明确错误信息
- 缺少必填字段返回明确错误信息
- 重复导入不会产生脏数据

**导出测试：**
- 返回 200 状态码和 Excel Content-Type
- 文件可被 openpyxl 解析
- 表头列名与列表页显示一致
- 数据行数与筛选条件匹配
- 中文字段无乱码

**边界测试：**
- 上传非 Excel 文件（如 .txt、.pdf）
- 上传超大文件（1000+ 行）
- 包含特殊字符的数据（换行符、引号、逗号）
- 导入数据中包含不存在的分公司/资产编号关联

## Capabilities

### New Capabilities

- `import-export-test-suite`: 完整的导入/导出自动化测试套件，覆盖 7 个模块 22 个功能端点的模板下载、批量导入、数据导出

### Modified Capabilities

_(无现有 spec 需要变更)_

## Impact

- **后端测试**: 新增 `backend/tests/test_import_export.py`，约 60-80 个测试用例
- **无业务代码变更**: 本提案仅添加测试，不修改任何业务逻辑
- **回归保障**: 后续任何导入/导出相关变更都可通过此套件快速验证

## Tasks

- [ ] 编写资产模块导入/导出/模板测试（Asset + FixedAsset，5 个端点）
- [ ] 编写分类模块导入/导出/模板测试（Category，3 个端点）
- [ ] 编写调拨模块 4 种类型的导入/导出/模板测试（Transfer purchase/assign/transfer/recovery，12 个端点）
- [ ] 编写盘点模块导入/模板测试（Inventory，2 个端点）
- [ ] 编写边界条件测试（空文件、错误格式、特殊字符、超大文件）
- [ ] 运行全量测试确认通过
