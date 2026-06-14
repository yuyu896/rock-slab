## Context

当前项目有 4 种不同的导入弹窗实现，模板下载方式各不相同：

| 模块 | 弹窗组件 | 模板下载方式 | 问题 |
|------|---------|-------------|------|
| 资产列表 | AssetImportDialog.vue | `GET /api/assets/export`（全量数据） | 下载的是全部数据，不是空模板 |
| 资产分类 | CategoryImportDialog.vue | `GET /api/categories/template`（专用 API） | 唯一正确的实现 |
| 采购页面 (Purchase) | PurchaseImportDialog.vue | 静态文件 `/xx分公司...模版.xlsx` | 静态文件可能不存在或空白 |
| 流转页面 (PurchaseList/TransferList/AssignList) | useTransferList 内联 | `GET /api/transfers/export`（全量数据） | 同资产的问题，无数据时可能空白 |

此外，资产的导入/导出列顺序需要调整，新增"图片"列。

## Goals / Non-Goals

**Goals：**
- 修复采购入库流转页的模板下载为空白的问题
- 调整资产模块导入/导出列顺序为指定的 23 列排列
- 为资产和流转模块新增专用模板下载 API
- 统一所有导入弹窗的模板下载方式（都调用专用模板 API）
- 统一所有导入弹窗的视觉样式和交互流程

**Non-Goals：**
- 不重构共享 `ImportDialog.vue` 组件为统一基类（各模块保留独立组件，仅统一样式）
- 不修改盘点模块的导入（它是按任务的特殊导入，逻辑不同）
- 不修改分类模块的已有实现（它已经有专用模板 API，只需统一样式）
- 不改变导入的数据处理逻辑，只修复模板下载

## Decisions

### 1. 新增专用模板 API 而非依赖全量导出

**决定**：为 assets 和 transfers 各新增一个 `download_template` action，返回仅含表头行的空 xlsx 文件。

**理由**：
- 分类模块已有 `download_template` 的成功先例（`categories/views.py` 第 101-127 行）
- 全量导出当模板有两个问题：1）数据量大时下载慢；2）无数据时可能只有表头甚至空白
- 模板 API 返回的表头与导入 parser 的列顺序严格一致，避免用户填错列

**替代方案（否决）**：前端用 xlsx 库本地生成模板 — 增加前端依赖，且列顺序需前后端双重维护。

### 2. 资产列顺序调整 — 同步修改导入和导出

**决定**：在 `assets/views.py` 中同步修改 `export_excel`、`import_excel` 和新增的 `download_template`，统一使用新的 23 列顺序。

**新列顺序**：
```
序号, 分公司, 资产编号, 分公司编号, 资产类目, 电脑序列号, 供应商,
物品分类, 资产名称, 图片, 入库日期, 是否租用, 数量, 规格, 单价,
购入金额, 出库日期, 所属部门, 使用人, 当前状态, 警戒线, 是否充足, 备注
```

**关键变化**：分公司编号与资产编号互换位置、电脑序列号从末尾提前到第 6 列、新增"图片"列（第 10 位）。

**导入处理**：图片列在导入时跳过（ImageField 不适合通过 Excel 导入），`row[9]` 读到后忽略。导出时输出图片 URL 字符串。

### 3. 统一弹窗样式 — 各组件独立但视觉一致

**决定**：保持各模块独立的弹窗组件（AssetImportDialog、CategoryImportDialog、PurchaseImportDialog、useTransferList 内联弹窗），但统一以下视觉元素：
- 弹窗标题格式："批量导入[模块名]"
- 统一按钮样式和布局：下载模板（次要按钮） + 选择文件 + 确认导入（主要按钮）
- 统一上传区域样式：虚线边框 + 图标 + 提示文字
- 统一导入结果展示：成功 N 条 / 失败 N 条 + 错误列表

**理由**：各模块的导入 API 和参数不同，强行共用组件会增加条件分支。统一样式更务实。

### 4. PurchaseImportDialog 改用 API 而非静态文件

**决定**：`PurchaseImportDialog.vue` 的模板下载从静态文件改为调用 `GET /api/assets/template`。

**理由**：静态文件 `/xx分公司行政资产盘点系统-模版.xlsx` 依赖 public 目录下的文件，不可靠且无法随列顺序变化自动更新。

### 5. 流转页面模板下载改用专用 API

**决定**：`useTransferList.ts` 中的 `downloadTemplate` 改为调用 `GET /api/transfers/template`。

**理由**：与资产模块同理，不再依赖全量导出。

## Risks / Trade-offs

- **[中风险] 资产列顺序变更影响已有用户**：已有用户可能按旧格式准备了 Excel，新顺序会导致导入列错位。→ 在模板文件名中加入日期或版本号，帮助用户区分。
- **[低风险] 图片列导入跳过**：用户在 Excel 中填写了图片路径也无法导入。→ 在导入结果中提示"图片列已跳过"。
- **[低风险] PurchaseImportDialog 调用资产模板 API**：采购页面（Purchase.vue）导入的是资产而非流转，使用资产模板 API 是正确的。→ 确认导入仍调用 `POST /api/assets/import`。
