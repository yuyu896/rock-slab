## 1. 固定资产创建路径修复（FixedAssetSerializer）

- [x] 1.1 在 `FixedAssetSerializer` 显式声明 `asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects.all(), required=False, allow_null=True)`
- [x] 1.2 新增 `FixedAssetSerializer.validate(attrs)`：当未提交 `asset` 且 `资产编号` 在品目表查不到时，抛出 `serializers.ValidationError({'资产编号': ['资产编号不存在']})`（返回 400、不录入）；反查成功时把 `asset` 放入 `attrs` 供 `create()` 复用
- [x] 1.3 确认 `create()` 中「`asset` 缺失但 `资产编号` 存在 → 按编号反查品目并关联」逻辑保持可用（[serializers.py:64-67](backend/apps/assets/serializers.py#L64-L67)），与 `validate()` 协同无重复查询问题
- [x] 1.4 确认继承字段（`资产名称`、`分公司`、`分公司编号`、`branch`）在反查成功后正确回填
- [x] 1.5 确认前端 `FixedAssetCreate.vue` 经 `handleApiError` + `ElMessage.error` 能把该 400 错误体弹为"资产编号不存在"提示（前端无需改动，仅人工验证）

## 2. 资产创建路径修复（AssetSerializer）

- [x] 2.1 在 `AssetSerializer.Meta` 增加 `extra_kwargs = {'序号': {'required': False}}`，解除 `序号` 必填
- [x] 2.2 新增 `AssetSerializer.create()`：当 `序号` 缺失时，取 `Asset.objects.order_by('-序号').first().序号 + 1` 自增赋值（空表时取 1）
- [x] 2.3 在 `create()` 中按提交的 `分公司`（名称）反查 `Branch`，回填 `branch` 外键与 `分公司编号`（仅当能解析到时；提交了 `branch` 时优先用 `branch`）
- [x] 2.4 确认 `分公司`、`分公司编号` 虽然 read_only，但在 `create()` 通过 `validated_data` 显式赋值可正常写入（参考 `FixedAssetSerializer.create()` 同样手法）
- [x] 2.5 新增 `AssetSerializer.validate()`：提交的 `资产编号` 必须在 `Category.asset_code` 中登记，否则抛 `ValidationError({'资产编号': ['该资产编号未在资产分类登记，请先在资产分类中添加']})`；更新时仅请求携带资产编号才校验

## 3. 测试补充

- [x] 3.1 在 `backend/tests/test_fixed_asset.py` 增加：仅传 `资产编号` 创建固定资产 → 201，`asset` 正确关联、继承字段已回填
- [x] 3.2 增加：`资产编号` 不存在 → 400 且错误信息明确
- [x] 3.3 增加：直接提交 `asset` 外键 → 201（已由既有 `test_create_instance_via_api` 覆盖）
- [x] 3.4 在资产相关测试中增加：不传 `序号` 创建资产 → 201，`序号` 为最大值+1
- [x] 3.5 增加：按分公司名称创建资产 → 201，`branch` 与 `分公司编号` 正确回填
- [x] 3.6 增加：显式传 `序号` 时予以保留
- [x] 3.7 增加：资产编号未在分类登记 → 400 且错误信息含「资产分类」

## 4. 验证

- [x] 4.1 运行 `pytest backend/tests/test_fixed_asset.py` 及资产相关测试，全部通过
- [ ] 4.2 本地启动前后端，在 `FixedAssetCreate.vue` 提交（仅资产编号 + 实例字段）→ 创建成功，列表可见且分公司/品目字段正确
- [ ] 4.3 在 `AssetCreatePage.vue` 提交（不填序号、选分公司）→ 创建成功，序号自增、分公司正确关联、列表按数据范围可见
- [x] 4.4 回归确认资产流转（采购/领用/调拨/回收）、Excel 导入路径未受影响（`test_transfers/test_import_export/test_data_scoping/test_inventories` 共 110 项全部通过）
