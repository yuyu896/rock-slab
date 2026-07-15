## Why

资产列表、固定资产表的分公司筛选**仍不生效**。根因（比上次 `fix-branch-filter` 更深一层）：

后端按 `分公司编号`(code) 过滤，但**导入的资产其「分公司编号」取自导入文件、由用户手填**（`import_excel` 第 213 行 `分公司编号=str(cell(row,'分公司编号'))`），常与分公司真实 code 不一致；而**单条创建**的资产由 `AssetSerializer.create` 回填了正确 code（按分公司名反查 Branch）。于是「按编号过滤」对**导入来源**的资产大量匹配不到——而线上多数资产来自导入，故筛选形同虚设。

上次 `fix-branch-filter` 只对齐了「前端发值 ↔ 后端过滤字段」（都按 code），**没有解决「导入资产的分公司编号本身不可靠」**这一数据层根因。

## What Changes

- **改为按分公司名称过滤**（名称在创建/导入时都按分公司名登记且校验，最可靠）：后端 `AssetFilterSet`/`FixedAssetFilterSet` 的 `branch` 由 `分公司编号` 改为 `分公司`；前端 `AssetList`/`FixedAssetList` 下拉值由 `b.code` 改回 `b.name`。
- **导入时由分公司名称反查 Branch 回填「分公司编号」**（不再读文件列），保证该字段正确一致；导入模板去掉「分公司编号」列（同序号/警戒线，系统派生）。
- 现有数据：按名称过滤**立即对所有资产生效**（无需回填）；历史「分公司编号」不一致仅影响该列展示（可选回填，见 Open Questions）。

## Capabilities

### New Capabilities
- `asset-branch-filter`: 资产/固定资产列表按分公司筛选可靠命中（按名称，兼容创建+导入两种来源），并保证导入回填正确的分公司编号。

### Modified Capabilities
<!-- 纠正上次 fix-branch-filter（branch-filter）中资产部分「按编号过滤」的做法——改为按名称。该提案尚未归档。 -->

## Impact

- **后端** `apps/assets/filters.py`（`branch` 过滤字段 `分公司编号`→`分公司`）、`apps/assets/views.py`（导入回填分公司编号 + 模板去分公司编号列）。
- **前端** `AssetList.vue`、`FixedAssetList.vue`（下拉值 `b.code`→`b.name`）。
- **测试**：导入资产（分公司编号≠code）按名称筛选命中、单条创建资产命中、导入回填编号。
- 无 DB 迁移；按名称过滤立即对全量资产生效。
