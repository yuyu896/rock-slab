## Context

资产分类模块前端 Category.vue 已实现完整 UI（属性模板编辑、Excel 导入弹窗、模板下载按钮），前端 API 层 `categories.ts` 也已定义了 `importCategories()` 和 `downloadCategoryTemplate()` 函数。但后端缺失对应支持：

- Category 模型没有 `attribute_template` 字段，前端保存的属性模板数据无法持久化
- CategoryViewSet（标准 `ModelViewSet`）没有 import 和 template 下载的自定义 action

后端已有 `openpyxl` 依赖（requirements.txt），且 `AssetViewSet` 中有成熟的 Excel 导入/导出模式可复用。

## Goals / Non-Goals

**Goals:**
- Category 模型新增 `attribute_template` JSONField，可存储动态属性模板配置
- Serializer 支持该字段的读写，与前端 attributes 数据格式对齐
- 新增 `GET /api/categories/template/` 端点，返回分类导入 Excel 模板文件
- 新增 `POST /api/categories/import/` 端点，接收 Excel 文件批量创建分类记录

**Non-Goals:**
- 不修改前端代码（前端已实现，只需后端对接）
- 不修改权限逻辑（现有 supervisor 写入权限已满足需求）
- 不修改 CategoryFilterSet

## Decisions

### 1. attribute_template 字段：JSONField + nullable

**选择**：使用 Django `models.JSONField(default=dict, blank=True)`
**理由**：
- 与前端 attributes 数组格式直接兼容（`[{name, type, required, options}]`）
- JSONField 是 Django 内置字段，无需额外依赖
- `default=dict` 保证已有数据不会因迁移出错

**备选**：单独建 AttributeTemplate 模型 — 过度设计，当前属性模板是每个分类的简单配置，不需要独立模型。

### 2. Excel 模板下载：内存生成

**选择**：在 `@action` 中用 openpyxl 内存创建模板 Workbook 并返回
**理由**：
- 无需维护静态模板文件
- 与 AssetViewSet 的导出模式一致
- 模板列：资产类目、物品分类、资产名称、资产编号、计量单位、警戒线、备注

### 3. Excel 导入：复用 AssetViewSet 模式

**选择**：`@action(detail=False, methods=['post'], parser_classes=[MultiPartParser])`，使用 openpyxl 逐行解析
**理由**：
- 与已有 `AssetViewSet.import_excel` 保持一致的代码风格
- 返回 `{imported, errors}` 格式，与前端期望的 `data.imported`、`data.errors` 对齐

## Risks / Trade-offs

- **attribute_template 数据验证**：JSONField 不做 schema 约束 → 在 serializer 的 `validate_attribute_template` 中校验基本结构（数组、每项含 name/type 字段）
- **Excel 导入数据质量**：用户可能上传格式错误的文件 → 逐行 try/except 捕获错误，返回行级错误信息
- **Migration 风险**：新增 nullable JSONField 对已有数据无影响 → 简单迁移，无数据丢失风险
