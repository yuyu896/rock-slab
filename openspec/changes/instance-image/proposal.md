# 实例档案物品图片

## Why

实例档案（FixedAsset，一物一档）目前只有文本字段，盘点核对、报废鉴定、纠纷对质时无法直接看到「这台设备长什么样」。给实例挂一张实物照片，是档案属性的补全，让「档」真正可看。品目字典虽有 `image` 字段（品目级通用图），但同品目下不同个体（不同成色、改装、序列号标签）需要实例级照片，两者不冗余。

## What Changes

- FixedAsset 模型新增 `image`（ImageField，`upload_to='fixed_assets/'`，可空）——档案属性，与序列号补录同构，不经流转单（铁律 2 管数量变动，图片不是数量）
- 新增实例图片端点：`POST /api/assets/fixed-assets/{id}/image`（multipart 上传，覆盖旧图）与 `DELETE .../image`（删除），均要求 `manage_instances` 操作码
- 上传校验与头像一致：jpeg/png/webp 白名单、≤2MB；更换/删除时清理旧文件防孤儿
- 序列化器输出 `图片`（图片 URL，只读）
- 实例表列布局：**图片列放在序号列后面（第二列）**，缩略图展示、点击放大预览
- 操作列新增「图片」按钮（`manage_instances` 可见）：弹窗内上传/更换/删除图片
- 非目标：Excel 导出不嵌图片（保持现有列）；移动端展示不在本次范围；一品目多图不做（单图够用，与 Category.image / users.avatar 口径一致）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fixed-asset-instance`: 实例档案模型新增图片字段；新增「实例图片端点」要求（上传/删除，manage_instances 权限，校验与文件清理）；「实例写接口冻结」口径从「除序列号补录外」扩展为「除序列号补录与图片维护外」
- `fixed-asset-table-columns`: 实例表列布局新增图片列（置于序号列前），操作列新增「图片」操作

## Impact

- **后端**: `apps/assets/models.py`（+migration）、`serializers.py`（图片输出）、`views.py`（image action ×2）；`core/upload_validation.py` 增加图片校验助手（复用头像同款规则）
- **前端**: `types/index.ts`（FixedAsset.图片）、`api/assets.ts`（上传/删除）、`views/FixedAssetList.vue`（图片首列 + 图片弹窗）
- **基础设施**: MEDIA 配置与生产 nginx `/media` 托管已就绪（头像链路已验证），无需改动
- **风险**: 图片属实例写路径，架构测试白名单需容纳新端点（仍禁止触碰状态/数量）
