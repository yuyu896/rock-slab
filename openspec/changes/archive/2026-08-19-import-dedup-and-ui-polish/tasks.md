## 1. 固定资产导入 DB 级查重

- [ ] 1.1 `import_excel`（固定资产）：预加载已有四元组集合；每行 create 前检查，存在则跳过+提醒

## 2. 导入行数限制

- [ ] 2.1 资产/固定资产导入：行数 > 200 时返回 400 提示分批

## 3. 操作按钮加大

- [ ] 3.1 `global.css` `.action-btn` padding 6px 12px → 8px 16px；svg 加大
- [ ] 3.2 `FixedAssetList.vue` `.action-col .action-btn` 同步调整

## 4. 资产列表表格固定高度

- [ ] 4.1 `AssetList.vue` `.table-container` 加 max-height + overflow-y: auto；thead sticky

## 5. 验证

- [ ] 5.1 pytest + vue-tsc
