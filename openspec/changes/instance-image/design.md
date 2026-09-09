# 实例物品图片 — 技术设计

## Context

实例档案现为纯文本字段（品目联字典 + 出生行派生）。系统已有两条图片链路先例：

- `users.avatar`：专用 `POST/DELETE /api/users/{id}/avatar` action，MultiPartParser，类型白名单（jpeg/png/webp）+ ≤2MB，覆盖时 `avatar.delete(save=False)` 清旧文件
- `categories.image`：模型 ImageField + 序列化器 `图片`（只读 URL，`image` write_only）

MEDIA 基础设施全链路就绪：`MEDIA_ROOT/MEDIA_URL`、开发 Vite 代理 `/media`、生产 rock-slab-nginx 托管 `/media`（头像已验证）。`core/upload_validation.py` 已有上传校验助手（Excel 用）。

约束：FixedAssetViewSet 冻结只读，唯一白名单写路径是 `supplement`（序列号/备注，`manage_instances`）；架构测试执法实例写操作收敛。铁律 2 管「台账数量变动必须走单据」——图片不是数量，是档案属性，与补录同构。

## Goals / Non-Goals

**Goals:**

- 实例挂单张物品图片：上传/更换/删除，`manage_instances` 权限
- 实例表图片列置于序号列前（第一列），缩略图 + 点击放大
- 上传校验与文件清理与头像口径完全一致

**Non-Goals:**

- 多图（一实例多角度照片）——单图覆盖列表场景，需要时另立提案
- Excel 导出嵌图片、移动端展示、生平抽屉挂图
- 品目字典 `image` 的前端启用（品目级通用图，另一条线）

## Decisions

### D1：单图 ImageField，不建多图关联表

`image = models.ImageField('物品图片', upload_to='fixed_assets/', blank=True, null=True)`，英文列名与 `Category.image`/`User.avatar` 对齐。多图需独立表 + 排序 + 逐图删除 UI，当前需求（列表看图对物）单图即答；升级路径是加表不动本字段。

### D2：专用 image action（单 action 双方法分流），不并入 supplement

`POST /api/assets/fixed-assets/{id}/image`（multipart，字段名 `image`）与 `DELETE` 同路径。supplement 是 JSON PATCH 且契约写死「仅 序列号/备注 两字段」——multipart 与 JSON 混在一个端点会让校验和写接口冻结口径都变模糊。

**实现要点（实施中修正）**：DRF 对同 url_path 的两个 `@action` 不合并路由，按方法名排序注册两条 URL pattern，先注册者遮蔽后者的 HTTP 方法——users 头像的 `POST /avatar` 405 即此坑（`delete_avatar` 按字母序先注册，生产一直 405，测试以 xfail 记录在案）。因此本端点用**一个 action 挂 `methods=['post', 'delete']`，handler 内按 `request.method` 分流**，一条 pattern 双方法，结构上免疫排序遮蔽。`required_operations` 挂 `'image': 'manage_instances'`（OperationPermission 按 action 名取码，双方法共用）。users 头像存量 405 是独立问题，另行提案处理。

### D3：校验规则抽到 core/upload_validation.py

新增 `validate_image_upload(file)`：Content-Type 白名单 `image/jpeg|png|webp`、≤2MB，违规抛 `UploadValidationError` → 视图转 400。规则与头像端点逐字一致，users 端后续可收编（本次不动 users，控范围）。Content-Type 不看扩展名（浏览器/代理常改写），与既有 Excel 校验「Content-Type 不作为拒绝依据」的注释口径互不冲突——图片校验看的是 DRF 已解析的 file.content_type，非裸 header。

### D4：覆盖/删除即清旧文件

`instance.image.delete(save=False)` 后赋新值/置空再 `save(update_fields=[...])`，与 users.avatar 同法，杜绝孤儿文件。退役实例图片随档案永久保留（不物理删除实例，铁律）。

### D5：前端图片列居序号后，el-image 朴素缩略图

- `types`：`FixedAsset` 加 `图片?: string | null`
- `api/assets.ts`：`uploadFixedAssetImage(id, file)`（FormData multipart）、`deleteFixedAssetImage(id)`
- `FixedAssetList.vue`：图片列置于序号列后（第二列）；已挂图 `el-image`（~40px，`object-fit: cover`，`preview-src-list` 点击放大）；未挂图灰色占位（相机图标或「暂无」）；操作列加「图片」按钮（相机 icon，`manage_instances` 可见）→ `el-dialog` 弹窗：当前图预览 + 隐藏 file input 上传（前端先校验类型/大小，同 UserPanel）+ 删除（ElMessageBox 确认）
- 上传/删除成功后就地更新该行 `图片` 字段（或整页刷新，取简）

### D6：架构测试天然放行 image 端点（无需改白名单）

实例写冻结的架构测试（`test_instance_binding.py::TestInstanceArchitecture`）执法方式是正则扫描 apps 代码：`当前状态/使用人/branch/department` 赋值 + `FixedAsset.objects.create/update/delete`。图片端点只写 `instance.image = upload` 与 `instance.image.delete(save=False)`，均不命中模式（与 supplement 的 `序列号 =` 同理），无需登记白名单；端点内仅 `save(update_fields=['image', 'updated_at'])`，不触碰状态/数量列，全量 pytest 实测通过。

## Risks / Trade-offs

- [媒体目录膨胀] → 2MB 上限 + 单图覆盖式（一实例至多一份文件）
- [列表序列化引入性能问题] → ImageField URL 序列化纯字符串拼接，无额外查询/IO，无 N+1
- [覆盖瞬间并发上传互相覆盖] → 与头像同口径，最后写赢；图片无对账属性，可接受
- [架构测试误伤] → 端点只写 image 列；实现时跑全量 pytest 验证

## Migration Plan

1. additive migration（可空字段，无数据回填；不涉及 SQLite/PG 方差——无 min(uuid) 类聚合）
2. 部署走既有 `deploy.sh`（migrate → collectstatic → nginx reload），无额外步骤
3. 回滚：字段可空，代码回退即回到无图状态；已上传文件留存无碍

## Open Questions

（无——单图/权限/列位均已在提案拍板）
