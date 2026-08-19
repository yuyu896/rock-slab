## 1. 资产列表改动

- [ ] 1.1 `Asset.资产编号` 去 `unique=True`（迁移 AlterField）
- [ ] 1.2 资产 `import_excel`：所属部门空 → 拒行；去重 key 改为 `(分公司, 资产编号, 所属部门, 规格)`
- [ ] 1.3 测试：不同所属部门/规格允许同编号；四元组全同判重复；所属部门空被拒

## 2. 固定资产解耦

- [ ] 2.1 `FixedAsset` 移除 `asset` 外键（迁移 RemoveField）；新增 `资产类目` 字段（迁移 AddField）
- [ ] 2.2 `import_excel`：去掉父资产查找；改为校验 资产编号 存在于 `Category.asset_code`；资产类目/物品分类/资产名称 缺省从品目取
- [ ] 2.3 移除 `signals.py` 的 `_sync_asset_counts` + 信号连接
- [ ] 2.4 导出 `export_excel`：序号/资产类目/物品分类/资产名称 改用 FixedAsset 自身字段（无父 Asset）
- [ ] 2.5 `serializers.py`：清理 FixedAssetSerializer 的 asset 字段引用
- [ ] 2.6 `views.py`：`select_related('asset')` 去掉
- [ ] 2.7 测试：固定资产品目校验（在/不在品目）；导入不再查父资产

## 3. 验证

- [ ] 3.1 后端 `pytest` 全绿
- [ ] 3.2 Django check / 迁移正常
- [ ] 3.3 本地手动：资产导入同编号不同部门可重复；固定资产导入品目校验
