## Context

- **TransferActionSerializer**：`调出分公司`/`调入分公司` 为 `required=False, allow_blank=True`；`资产编号`/`资产名称` 为必填（CharField 默认 required=True）；无电脑序列号字段。
- **AssetSerializer**：`分公司`/`资产编号`/`资产名称` 为模型字段（CharField，非 blank），但 extra_kwargs 里 `序号` required=False；validate 检查编号在品目。
- **FixedAssetSerializer**：`分公司`/`资产编号`/`资产名称` 在 fields 里但模型字段为 `blank=True`；无必填校验。有 `序列号` 字段。

## Decisions

### 决策 1：后端序列化器统一加必填
- **TransferActionSerializer**：`调出分公司` 改为 `required=True`（不再 allow_blank）。
- **FixedAssetSerializer.validate**：加分公司/资产名称/序列号非空校验（资产编号已校验品目存在）。
- **AssetSerializer**：已有模型层非 blank 约束，确认前端表单也校验。

### 决策 2：前端表单已有校验的确认一致
- AssetCreatePage：已有分公司/编号/名称必填（`v-if` 提交校验）。
- 其他表单：检查并补齐。

## Open Questions
（暂无。）
