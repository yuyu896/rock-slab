# 实例物品图片 — 实施任务

## 1. 后端模型与序列化

- [x] 1.1 FixedAsset 模型加 `image = models.ImageField('物品图片', upload_to='fixed_assets/', blank=True, null=True)`，生成并检查 migration（可空、无数据回填）
- [x] 1.2 `FixedAssetSerializer` 加 `图片 = serializers.ImageField(source='image', read_only=True)`（fields 列表加入 `图片`），确认列表/详情/生平均输出图片 URL

## 2. 校验助手与图片端点

- [x] 2.1 `core/upload_validation.py` 新增 `validate_image_upload(file)`：Content-Type 白名单（image/jpeg、image/png、image/webp）、≤2MB，违规抛 `UploadValidationError`
- [x] 2.2 `FixedAssetViewSet` 加 `image` action：`POST /api/assets/fixed-assets/{id}/image`（MultiPartParser，字段 `image`）与 `DELETE` 同路径；`required_operations` 挂 `manage_instances`
- [x] 2.3 端点实现：校验 → 旧文件 `delete(save=False)` → 赋值/置空 → `save(update_fields=['image', 'updated_at'])` → 返回完整实例序列化数据；UploadValidationError 转 400
- [x] 2.4 架构测试白名单按 `supplement` 先例纳入 image 端点（断言仍禁触碰状态/数量列）

## 3. 后端测试

- [x] 3.1 上传成功：返回 200、`图片` 指向 `/media/fixed_assets/…`、文件落盘
- [x] 3.2 校验拒绝：gif 格式 400、3MB 超限 400，实例图片无变化
- [x] 3.3 覆盖与删除：覆盖后旧文件被清理；DELETE 后字段为空且文件删除
- [x] 3.4 权限：无 `manage_instances` 调用上传/删除被拒；请求夹带状态字段不生效
- [x] 3.5 全量 pytest（含架构测试与对账）通过

## 4. 前端类型与 API

- [x] 4.1 `types/index.ts`：`FixedAsset` 加 `图片?: string | null`
- [x] 4.2 `api/assets.ts`：`uploadFixedAssetImage(id, file)`（FormData multipart）、`deleteFixedAssetImage(id)`

## 5. 前端列表页

- [x] 5.1 `FixedAssetList.vue`：表头与行首插「图片」列（序号列前）；已挂图 `el-image` 缩略图（~40px，cover，点击放大），未挂图占位标识；colspan 同步 +1
- [x] 5.2 操作列加「图片」按钮（相机 icon，`canSupplement` 同权限可见）→ 弹窗：当前图预览 + 上传/更换（前端先校验类型/大小，同 UserPanel）+ 删除（确认框）
- [x] 5.3 成功后就地更新该行 `图片` 字段并提示；失败走 `handleApiError`
- [x] 5.4 `npm run build` 类型检查通过；补 vitest（列序/权限可见性至少一条）

## 6. 验收与收尾

- [x] 6.1 本地手验：dev 起前后端，实例页上传/预览/更换/删除全流程走通（凭据见维护手册）
- [x] 6.2 核对铁律两问：信息只存一处（实例图≠品目图）、不涉台账数量；`check_ledger_consistency` 不受影响
