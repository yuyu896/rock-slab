## Context

`assets` app 的两个 `ModelSerializer`（`AssetSerializer`、`FixedAssetSerializer`）当前在创建路径上被 DRF 的字段必填推断阻断：

- **固定资产**：`FixedAsset.asset` 外键在模型层无 `null=True`（[models.py:64](backend/apps/assets/models.py#L64)），`ModelSerializer` 将其推断为 `required=True`。前端 `FixedAssetCreate.vue` 只提交 `资产编号`，请求在 `is_valid()` 阶段即报 `{"asset": ["该字段是必填项。"]}` 返回 400。而 `FixedAssetSerializer.create()` 本已写好「仅传资产编号、按编号反查品目」的兜底（[serializers.py:58-76](backend/apps/assets/serializers.py#L58-L76)），只是永远执行不到。
- **资产（品目）**：`Asset.序号` 为 `IntegerField` 无 `default/null/blank`（[models.py:14](backend/apps/assets/models.py#L14)），且不在 `read_only_fields`（[serializers.py:22](backend/apps/assets/serializers.py#L22)），被推断为必填。前端 `AssetCreatePage.vue` 不提交 `序号`，同样在 `is_valid()` 返回 400。

附带发现：`AssetSerializer` 没有 `create()` 重写，且 `分公司`/`分公司编号` 是 read_only。即使单独修复 `序号`，前端提交的 `分公司`（分公司**名称**）也会被丢弃、`branch` FK 又未提交，导致创建出的资产行 `分公司=''`、`分公司编号=''`、`branch=None`，破坏 `DataScopeMixin`（`scope_branch_field='branch'`）的数据隔离。因此资产创建路径需一并补全分公司解析。

既有可复用模式：`FixedAssetSerializer.create()` 已实现「按字段反查关联对象并补全冗余字段」；`TransferViewSet._create_action()` 已实现「按分公司名称反查 `Branch`」。

## Goals / Non-Goals

**Goals:**
- `POST /api/assets/fixed-assets` 在仅传 `资产编号`（及其余实例字段）时返回 201，并正确关联父级品目。
- `POST /api/assets/` 在不传 `序号` 时返回 201，由后端自增序号；并按提交的分公司名称正确关联 `branch`、回填 `分公司`/`分公司编号`。
- 两条创建路径都有自动化测试覆盖，防止回归。

**Non-Goals:**
- 不改模型字段定义、不新增数据库迁移。
- 不改前端（`FixedAssetCreate.vue`、`AssetCreatePage.vue` 现有 payload 即为修复目标）。
- 不重构 Excel 导入路径（`import_excel` 直接调用 `Asset.objects.create()`，绕过序列化器，不受影响）。
- 不调整资产流转（transfers）等其他已正常的创建入口。

## Decisions

### 决策 1：固定资产 —— 显式声明 `asset` 为非必填，复用既有 `create()` 反查
在 `FixedAssetSerializer` 显式声明：
```python
asset = serializers.PrimaryKeyRelatedField(
    queryset=Asset.objects.all(), required=False, allow_null=True,
)
```
保留 `create()` 中已有的「`asset` 缺失但 `资产编号` 存在 → 按编号反查」逻辑。

**为什么不用「前端先查品目 UUID 再提交 `asset`」**：会要求前端多一次查询、改动前端表单，且与既有「按资产编号创建」的产品意图相悖。后端放宽校验是更小、更贴合既有设计的改动。

### 决策 2：资产 —— `序号` 改为非必填，`create()` 中自增生成
通过 `extra_kwargs = {'序号': {'required': False}}` 放宽校验；新增 `AssetSerializer.create()`，当 `序号` 缺失时取 `Asset.objects.order_by('-序号').first().序号 + 1`（与 `TransferViewSet.warehouse()` 的 `max_seq + 1` 写法一致）。

**为什么不把 `序号` 加入 `read_only_fields`**：保持字段可写以兼容潜在的编辑场景；仅在缺失时补默认值，语义更清晰，且对更新路径零影响。

### 决策 3：资产 —— `create()` 中按分公司名称解析 `branch` 并回填冗余字段
新增 `AssetSerializer.create()`：若提交了 `分公司`（名称）但未提交 `branch`，按名称查询 `Branch`，回填 `branch`、`分公司`、`分公司编号`（与 `FixedAssetSerializer.create()` / `TransferViewSet._create_action()` 同一模式）。仅当能解析到分公司时回填，解析不到不阻断创建（保持与既有 `update()` 容错一致）。

**为什么必须包含此项**：否则修复 `序号` 后创建会产出无分公司的资产行，直接破坏按分公司的数据隔离与列表过滤，属于不完整修复。

### 决策 4：固定资产资产编号不存在 → 拒绝录入并前端提示（已确认）
当请求未提交 `asset` 外键、且 `资产编号` 在品目表中不存在时，系统 SHALL **不创建**实例，返回 **400**，错误体为 `{"资产编号": ["资产编号不存在"]}`。该校验放在 `FixedAssetSerializer.validate()`（在入库前拦截，比 `create()` 抛错更符合 DRF 校验惯例；反查成功时顺带把 `asset` 放入 `attrs` 供 `create()` 复用）。

前端 `FixedAssetCreate.vue` 复用既有 `handleApiError` + `ElMessage.error`（[request.ts:49-60](frontend/src/utils/request.ts#L49-L60)）将该字段错误以 toast 弹出"资产编号不存在"，**无需改前端代码**。

### 决策 5：测试在序列化器/视图层补充，复用既有测试文件
在 `backend/tests/test_fixed_asset.py` 增补「仅传资产编号创建固定资产」用例；在资产相关测试中增补「不传序号、按分公司名称创建资产」用例，断言 `序号` 自增、`branch`/`分公司编号` 正确回填。

### 决策 6：资产编号必须在资产分类登记（本地测试中发现并确认）
在 `AssetSerializer.validate()` 中校验：提交的 `资产编号` 必须存在于 `Category.asset_code`，否则抛 `ValidationError({'资产编号': ['该资产编号未在资产分类登记，请先在资产分类中添加']})`。校验对创建必触发（资产编号为必填项）；对更新仅在请求携带 `资产编号` 时触发（`attrs.get('资产编号') is not None`），避免影响历史脏数据的其他字段更新。Excel 导入路径（`import_excel` 直接 `Asset.objects.create()`）不在本决策范围。

**为什么后端校验而非前端下拉受控**：与固定资产新增校验同源、最稳妥；前端 `handleApiError` 自动弹提示，无需改前端。

## Risks / Trade-offs

- **[序号自增的并发竞态]** → 两个并发请求可能取到相同 `max+1`，产生重复序号。当前 `序号` 无唯一约束，与既有 `warehouse()` 路径风险等同，本变更不引入新风险；如需强唯一可后续加 `UniqueConstraint`（列为非目标，需迁移）。
- **[按名称反查分公司存在重名/不存在]** → 名称在系统中非唯一保证；若重名取首条。与 `TransferViewSet` 既有行为一致，保持系统内一致语义。
- **[放宽 `asset` 必填后，品目不存在时静默置空]** → 已规避：资产编号反查不到时在 `validate()` 阶段直接拒绝（决策 4），不会产出孤儿实例。

## Open Questions

无。资产编号不存在的处理已确定：拒绝录入并返回 400（见决策 4）。
