## 1. 固定资产导入表头校验

- [ ] 1.1 `import_excel`：解析表头后，校验列名集合 == FA_TEMPLATE_HEADERS；不一致 → 400 提示缺少/多余列

## 2. 固定资产列表序号

- [ ] 2.1 `FixedAssetList.vue`：v-for 加 index；序号改 `(page-1)*pageSize + index + 1`

## 3. 验证

- [ ] 3.1 pytest 全绿 + vue-tsc 通过
