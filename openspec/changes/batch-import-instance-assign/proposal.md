## Why

实例管理品目（如电脑、手机）无法通过批量导入领用，因为 Excel 模板缺少指定内部编号的机制。导入时预检会拒绝：「实例管理品目必须选择与数量等长的实例（请在页面单据中操作）」。这导致批量领用实例管理品目时，必须逐台手工在页面操作，效率低下。

## What Changes

- 在领用单批量导入模板中增加「内部编号」列
- 实例管理品目：每行填一个内部编号，数量固定为 1
- 数量管理品目：编号列留空，数量列正常填写
- 继续接受不含「内部编号」列的旧领用模板，保障数量管理品目的现有导入流程
- 导入时按内部编号查询实例并绑定到单据行
- 增加针对实例管理品目的特定校验规则
- 导入含实例管理品目的行时，要求操作者具有「查看实例档案」权限

## Capabilities

### New Capabilities
- `batch-import-with-instances`: 批量导入领用单时支持通过内部编号指定实例

### Modified Capabilities
<!-- 无现有能力的需求变更 -->

## Impact

- **后端**：
  - `backend/apps/transfers/views.py`：修改 `TYPE_TEMPLATES['assign']` 添加「内部编号」列，修改 `import_excel` 方法解析编号并查询实例
- **前端**：
  - `frontend/src/utils/importTemplate.ts`：同步更新页面本地生成的领用模板表头
- **现有校验逻辑**：
  - `backend/apps/transfers/services.py` 中的 `validate_line_items_instances` 已具备完整校验能力，无需修改
- **权限**：
  - 沿用单据创建路径；实例管理品目还要求 `view_instances`
- **向后兼容**：
  - 数量管理品目导入流程不变（编号列留空）
  - 实例管理品目从「无法导入」变为「可导入」，无破坏性变更
