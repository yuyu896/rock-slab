## Decisions

### 决策 1：表头集合校验（顺序无关）
- 上传表头集合 == FA_TEMPLATE_HEADERS 集合 → 通过；否则拒绝，提示缺少/多余列。
- 顺序不限（导入按列名映射，顺序本就无关）。

### 决策 2：序号计算行号
- `v-for="(item, index) in assets"` + `{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}`，与 AssetList 一致。
