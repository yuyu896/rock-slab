## Why

当前 AssetViewSet 是 ReadOnlyModelViewSet，资产只能通过流转模块间接变更。实际业务中，行政主管及以上角色需要直接编辑/修正资产信息（如更正名称、调整分类、删除错误录入），而行政组长和专员只需查看。缺少直接的编辑/删除能力导致数据纠错必须走导入流程，效率低下。

## What Changes

- 后端 AssetViewSet 从 `ReadOnlyModelViewSet` 升级为 `ModelViewSet`，暴露 update/partial_update/destroy 端点
- 新增角色权限控制：admin/manager/supervisor 可对自己数据范围内的资产执行编辑和删除；leader/staff 仅保留只读
- 编辑和删除操作同样受 DataScopeMixin 约束，只能操作自己区域/分公司内的资产
- 前端 AssetList.vue 增加编辑和删除按钮（仅 supervisor 及以上角色可见）
- 前端新增资产编辑表单/抽屉，复用 AssetSerializer 的字段

## Capabilities

### New Capabilities

- `asset-crud`: 资产直接编辑和删除能力，包含后端 CRUD 端点、角色权限控制和前端 UI

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- **后端**: `assets/views.py`（ViewSet 升级 + 权限装饰器）、`assets/serializers.py`（可能调整 read_only_fields）
- **前端**: `views/AssetList.vue`（增加编辑/删除操作）、`api/assets.ts`（已有 updateAsset/deleteAsset，可直接使用）
- **API 变更**: 新增 PUT/PATCH/DELETE `/api/assets/{id}/` 端点
- **权限**: supervisor(L3) 及以上可编辑/删除，leader(L4)/staff(L5) 只读
