## Context

当前 AssetViewSet 继承 `ReadOnlyModelViewSet`，仅暴露 list/retrieve。资产信息只能通过流转模块（采购入库、领用、调拨等）间接变更。前端 `api/assets.ts` 已定义 `updateAsset`/`deleteAsset` 函数，但后端无对应端点（会返回 405）。

数据隔离已由 `DataScopeMixin` 实现：admin/manager 看全部，supervisor 按大区过滤，leader/staff 按分公司过滤。Asset 模型有 FK `branch`（→ Branch）和 CharField `分公司` 双字段。

## Goals / Non-Goals

**Goals:**
- admin/manager/supervisor 可对数据范围内的资产执行编辑和删除
- leader/staff 保留只读，不暴露编辑/删除按钮和端点
- 编辑时同步更新 CharField `分公司`/`分公司编号`（与 FK `branch` 保持一致）
- 前端表格行内增加编辑和删除操作入口

**Non-Goals:**
- 不改变资产新增的流程（新增仍走导入或 AssetCreateForm 的现有逻辑）
- 不改变流转模块的资产同步机制
- 不做批量编辑/批量删除

## Decisions

### 1. ViewSet 从 ReadOnly 升级为 ModelViewSet

使用 `viewsets.ModelViewSet` 但通过 `get_permissions()` 按 action 动态控制权限：
- `list`/`retrieve`/`template`/`export` → `min_role='staff'`（所有人可读）
- `update`/`partial_update`/`destroy`/`import_excel` → `min_role='supervisor'`（仅 L1-L3）

替代方案：保持 ReadOnly + 单独注册 update/destroy action → 放弃，因为需要额外的 URL 路由且不够标准。

### 2. Serializer 中 branch 关联字段处理

编辑时如果 `branch` FK 被修改，需要在 `update()` 中同步更新 `分公司`（branch.name）和 `分公司编号`（branch.code），保持双字段一致性。将这两个 CharField 设为 `read_only=True`，由 serializer 的 `update()` 方法自动从 `branch` FK 填充。

### 3. 前端权限判断

使用已有的 `usePermission()` hook（检查 `user.role` level）控制编辑/删除按钮的显隐。supervisor(level≤3) 及以上显示操作按钮，以下隐藏。复用现有的 `AssetDetailDrawer` 展开编辑模式。

### 4. 删除使用硬删除

用户已明确过删除是真正删除记录，与停用不同。直接调用 `instance.delete()`，前端加二次确认弹窗。

## Risks / Trade-offs

- **误删风险** → 前端二次确认弹窗，提示"此操作不可恢复"
- **编辑冲突** → DRF 的 update 已有乐观锁（updated_at 字段），暂不做额外处理
- **分公司字段不一致** → 通过 serializer `update()` 自动同步，不依赖前端传值
