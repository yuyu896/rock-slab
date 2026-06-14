## 1. 后端 — FixedAsset 模型

- [x] 1.1 `assets/models.py`：新增 FixedAsset 模型（字段：asset FK、内部编号、资产编号、序列号、供应商、使用人、所属部门、状态、分公司/branch、入库日期、备注）
- [x] 1.2 `assets/models.py`：FixedAsset 内部编号自动生成方法（{资产编号}-{序号}）
- [x] 1.3 生成并应用数据库迁移

## 2. 后端 — 数量同步信号

- [x] 2.1 `assets/signals.py`：post_save/post_delete 信号，FixedAsset 变更时自动重新计算关联 Asset 的数量

## 3. 后端 — API

- [x] 3.1 `assets/serializers.py`：新增 FixedAssetSerializer
- [x] 3.2 `assets/views.py`：新增 FixedAssetViewSet（CRUD + DataScopeMixin + 权限控制）
- [x] 3.3 `assets/urls.py`：注册 fixed-assets 路由
- [x] 3.4 `assets/filters.py`：新增 FixedAssetFilterSet（按分公司/状态/关键词/资产编号筛选）

## 4. 后端 — Excel 导入

- [x] 4.1 `assets/views.py`：FixedAssetViewSet 新增 import_excel / download_template action
- [x] 4.2 导入时校验资产编号是否存在，自动生成内部编号

## 5. 后端 — 测试

- [x] 5.1 测试：创建 FixedAsset 实例后 Asset 数量同步
- [x] 5.2 测试：删除实例后 Asset 数量同步
- [x] 5.3 测试：内部编号自动递增
- [x] 5.4 测试：API 权限（supervisor 可写，staff 只读）
- [x] 5.5 测试：导入模板和批量导入

## 6. 前端 — 固定资产表页面改造

- [x] 6.1 `api/assets.ts`：新增 getFixedAssets / updateFixedAsset / deleteFixedAsset / importFixedAssets API 函数
- [x] 6.2 `FixedAssetList.vue`：改为调用 FixedAsset API，展示实例数据（内部编号、序列号、供应商、使用人、状态）
- [x] 6.3 `FixedAssetList.vue`：supervisor 及以上显示编辑和删除按钮
- [x] 6.4 `FixedAssetList.vue`：新增导入功能按钮和弹窗

## 7. 数据迁移

- [ ] 7.1 编写数据迁移脚本：将现有 Asset 中 资产类目='固定' 的记录，按数量拆分为 FixedAsset 实例
