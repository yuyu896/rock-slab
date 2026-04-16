## Why

资产分类模块前端已实现属性模板编辑 UI 和 Excel 导入/下载功能，但后端缺少对应支持：Category 模型没有 `attribute_template` 字段导致属性模板数据无法持久化，且缺少 Excel 模板下载和批量导入两个 API 端点。需要补齐后端实现以使前后端功能对接完整。

## What Changes

- Category 模型新增 `attribute_template`（JSONField），存储分类动态属性模板配置
- CategorySerializer 新增 `attribute_template` 字段的读写支持
- CategoryViewSet 新增 `GET /api/categories/template/` 端点，返回分类导入 Excel 模板文件
- CategoryViewSet 新增 `POST /api/categories/import/` 端点，接收 Excel 文件批量导入分类数据
- 新增 Django 数据库迁移文件

## Capabilities

### New Capabilities
- `category-attribute-template`: Category 模型 attribute_template JSONField 及 serializer 读写支持
- `category-excel-import`: 分类 Excel 模板下载端点和批量导入端点

### Modified Capabilities

## Impact

- **后端模型**: `backend/apps/categories/models.py` 新增 `attribute_template` 字段
- **后端序列化器**: `backend/apps/categories/serializers.py` 新增字段映射
- **后端视图**: `backend/apps/categories/views.py` 新增两个 `@action` 端点
- **数据库**: 需要 migration，对已有数据无破坏性（字段可为空）
- **依赖**: 可能需要 `openpyxl` 库处理 Excel 文件（需检查是否已有）
- **前端**: 无需修改，已有完整 UI 实现
