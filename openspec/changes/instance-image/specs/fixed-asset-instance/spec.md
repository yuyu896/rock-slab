# fixed-asset-instance 增量

## MODIFIED Requirements

### Requirement: 实例档案模型

FixedAsset MUST 为四态实例档案：字段含 `item`（→品目字典，PROTECT）、`内部编号`（唯一，`{品目编号}-{序号}`，锁行计数器生成）、`序列号`（空=待补录）、`当前状态`（在库/在用/回收库/退役，退役为终态）、`使用人`（记录性文本）、`department`（→部门字典 FK，可空）、`branch`（→分公司 FK）、`birth_line`（→出生采购明细行 FK，可空=存量迁移）、`入库日期`、`备注`、`image`（物品图片，ImageField 可空，`upload_to='fixed_assets/'`，单张，档案属性非数量）。模型 MUST NOT 存放资产编号/名称/规格/类目/供应商/单价等品目文本列——品目信息经 `item` 联字典输出，供应商/单价/采购日期经出生行派生输出（决策 #8）；物品图片与品目字典 `image`（品目级通用图）为两级不同信息，各自只存一处（铁律 1）。实例 MUST NOT 被物理删除。

#### Scenario: 品目信息联字典输出

- **WHEN** 客户端请求实例列表
- **THEN** 每行输出品目编号/名称/规格/类目/管理方式（item 联查）与供应商/单价/采购日期（出生行派生），实例表无冗余文本列

#### Scenario: 物品图片档案字段输出

- **WHEN** 实例已上传物品图片且客户端请求其详情或列表
- **THEN** 序列化输出含 `图片`（图片完整 URL）；未上传图片的实例该字段为空

#### Scenario: 退役实例档案保留

- **WHEN** 某实例经回收直接处置转入退役态
- **THEN** 该实例记录仍在库中且可查询，MUST NOT 出现任何物理删除路径

### Requirement: 实例写接口冻结

除序列号补录与物品图片维护外，实例的全部写接口（create/update/partial_update/destroy/batch-delete/导入）MUST 下线并返回 405/410，提示「实例变动请经流转单」。图片维护端点 MUST 仅触碰 `image` 字段（图片是档案属性，不是数量变动，铁律 2 不适用）；实例状态/使用人/分公司的全部变动 MUST 收敛于 `assets/services/instances.py`（由台账唯一写入口 `ledger.apply_document` 同事务调用）；架构测试 MUST 执法——services/migrations/tests 白名单之外的实例写操作即测试失败（图片端点同样 MUST NOT 触碰状态/数量列）。

#### Scenario: 手动创建实例被拒

- **WHEN** 用户 POST /api/fixed-assets/
- **THEN** 返回 405 与「实例出生=采购单」提示

#### Scenario: 图片端点不越权改状态

- **WHEN** 图片上传/删除请求体中夹带 当前状态 或 使用人 字段
- **THEN** 仅 `image` 字段生效，状态/使用人等档案字段无任何变化

#### Scenario: 架构测试抓到越权实例写

- **WHEN** 某视图代码直接修改 FixedAsset.当前状态
- **THEN** 架构测试失败并指出违规文件

## ADDED Requirements

### Requirement: 实例物品图片端点

系统 MUST 提供实例物品图片维护端点：`POST /api/assets/fixed-assets/{id}/image`（multipart，文件字段 `image`，上传或覆盖）与 `DELETE /api/assets/fixed-assets/{id}/image`（删除图片）。两端点均 MUST 要求 `manage_instances` 操作码，无权限 MUST 拒绝。上传校验 MUST 与头像口径一致：Content-Type 白名单（image/jpeg、image/png、image/webp）、大小 ≤2MB，违规返回 400。覆盖与删除时 MUST 清理旧存储文件（不留孤儿文件）。成功响应 MUST 返回更新后的实例序列化数据（含 `图片` URL）。

#### Scenario: 上传物品图片

- **WHEN** 持 `manage_instances` 的用户对某实例上传 1MB 的 JPG 文件
- **THEN** 返回 200，实例 `图片` 指向 `/media/fixed_assets/…` 下新文件，列表对应行显示缩略图

#### Scenario: 非白名单格式被拒

- **WHEN** 上传 image/gif 文件
- **THEN** 返回 400 提示仅支持 JPG、PNG、WebP，实例图片无变化

#### Scenario: 超大文件被拒

- **WHEN** 上传 3MB 的 PNG 文件
- **THEN** 返回 400 提示大小上限 2MB，实例图片无变化

#### Scenario: 覆盖图片清理旧文件

- **WHEN** 实例已有图片 A，再次上传图片 B 成功
- **THEN** 实例 `图片` 指向 B 的存储文件，A 的存储文件被删除

#### Scenario: 删除物品图片

- **WHEN** 持 `manage_instances` 的用户对已挂图实例调用 DELETE 图片端点
- **THEN** 返回 200，实例 `图片` 为空且存储文件被删除

#### Scenario: 无权限上传被拒

- **WHEN** 不持 `manage_instances` 的用户调用图片上传或删除端点
- **THEN** 返回权限不足错误，实例与存储均无变化
