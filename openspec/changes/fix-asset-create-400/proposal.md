## Why

新增固定资产（`POST /api/assets/fixed-assets`）和新增资产（`POST /api/assets/`）两个接口在正常提交时返回 **400 Bad Request**，导致对应的前端新增页（`FixedAssetCreate.vue`、`AssetCreatePage.vue`）无法创建数据。根因是同一类问题：`assets` app 的两个 `ModelSerializer` 让模型层无 `default`/`null` 的字段（固定资产的 `asset` 外键、资产的 `序号`）被自动推断为必填，在 `is_valid()` 阶段就拒绝请求，使 serializer `create()` 中已写好的兜底逻辑（按资产编号反查品目、自增序号）永远执行不到。

## What Changes

- **固定资产新增**：`FixedAssetSerializer` 的 `asset` 外键改为非必填（`required=False, allow_null=True`），使 `create()` 中「仅传资产编号、按编号反查关联品目」的既有逻辑能真正生效。
- **资产新增**：`AssetSerializer` 的 `序号` 改为非必填，在 `create()` 中由后端自增生成（取当前最大序号 +1），前端新增表单不再需要、也不应手填 `序号`。
- **资产编号受控**：`AssetSerializer` 新增 `validate()`，要求提交的 `资产编号` 必须已在资产分类（Category）的 `asset_code` 中登记，否则返回 400 提示「该资产编号未在资产分类登记」——堵住手填未登记编号即创建成功的存量漏洞。
- **回归校验**：补齐两个新增接口的接口/单元测试，覆盖「仅传资产编号创建固定资产」「不传序号创建资产」「资产编号未登记被拒」等路径，防止再次回归。

## Capabilities

### New Capabilities
- `asset-create-validation`: 资产（品目）与固定资产（实例）通过 API 创建时的字段校验与默认值规则——哪些字段由前端提交、哪些由后端补全（资产编号反查品目、序号自增），保证不传这些字段时创建成功而非 400。

### Modified Capabilities

## Impact

**后端**：
- `backend/apps/assets/serializers.py` — `FixedAssetSerializer` 显式声明 `asset` 为非必填；`AssetSerializer` 将 `序号` 设为非必填并在 `create()` 中自增赋值。
- `backend/tests/test_fixed_asset.py`（及资产创建相关测试）— 补充创建路径用例。

**前端**：无需改动。`FixedAssetCreate.vue`、`AssetCreatePage.vue` 现有提交 payload 不变，修复后即可正常创建。

**数据模型**：不改模型字段定义（不动迁移），仅在序列化器层放宽校验并补默认值。

**API 行为**：`序号`、`asset` 不再是请求必填项；两个新增接口对合法输入返回 201。
