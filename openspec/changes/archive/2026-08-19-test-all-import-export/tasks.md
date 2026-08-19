## 1. 测试基础设施搭建

- [x] 1.1 创建 `backend/tests/test_import_export.py` 文件，编写共享 helper 函数：`_make_xlsx(headers, rows)` 构造内存 Excel、`_parse_excel_response(response)` 解析响应中的 Excel、`_create_test_assets()` 创建测试资产数据、`_create_test_branches()` 创建测试分公司数据
- [x] 1.2 编写认证 fixture：复用 conftest.py 中的 `_client_for` 创建不同角色的认证客户端

## 2. 资产模块导入/导出/模板测试 (Asset)

- [x] 2.1 测试资产模板下载：`GET /api/assets/template` 返回 200 + Excel Content-Type + 表头列名验证（23 列）
- [x] 2.2 测试资产批量导入正常流程：上传 3 条数据 → 验证 imported=3 + 数据库记录字段正确
- [x] 2.3 测试资产批量导入空文件：只有表头 → 验证 imported=0
- [x] 2.4 测试资产批量导入非 Excel 文件：上传 .txt → 验证返回 400
- [x] 2.5 测试资产导出正常流程：先创建数据 → 导出 → 验证 Excel 行数和字段值
- [x] 2.6 测试资产导出空数据：无数据 → 验证仅含表头

## 3. 固定资产模块导入/模板测试 (FixedAsset)

- [x] 3.1 测试固定资产模板下载：`GET /api/assets/fixed-assets/template` 返回 200 + 表头列名验证
- [x] 3.2 测试固定资产批量导入正常流程：上传数据 → 验证 imported 数和字段正确性

## 4. 分类模块导入/导出/模板测试 (Category)

- [x] 4.1 测试分类模板下载：`GET /api/categories/template` 返回 200 + 表头列名验证（7 列）
- [x] 4.2 测试分类批量导入正常流程：上传 3 条分类 → 验证 imported=3 + 字段正确
- [x] 4.3 测试分类导入重复资产编号：导入已存在的 asset_code → 验证返回错误信息（实际行为：create() 触发唯一约束错误，记录在 errors 中）
- [x] 4.4 测试分类导出正常流程：先创建分类 → 导出 → 验证 Excel 行数

## 5. 调拨模块 — 采购类型测试 (Transfer/purchase)

- [x] 5.1 测试采购模板下载：`GET /api/transfers/template?type=purchase` → 验证表头包含采购相关列
- [x] 5.2 测试采购批量导入：上传采购数据 → 验证 imported 数 + 供应商/单价/总金额/需求部门/采购经办人/用途字段正确
- [x] 5.3 测试采购导出：创建采购记录 → 导出 → 验证 Excel 仅含采购类型数据

## 6. 调拨模块 — 领用类型测试 (Transfer/assign)

- [x] 6.1 测试领用模板下载：`GET /api/transfers/template?type=assign` → 验证表头列名
- [x] 6.2 测试领用批量导入：上传领用数据 → 验证记录正确入库
- [x] 6.3 测试领用导出：创建领用记录 → 导出 → 验证类型过滤正确

## 7. 调拨模块 — 调拨类型测试 (Transfer/transfer)

- [x] 7.1 测试调拨模板下载：`GET /api/transfers/template?type=transfer` → 验证表头列名
- [x] 7.2 测试调拨批量导入：上传调拨数据 → 验证记录正确入库
- [x] 7.3 测试调拨导出：创建调拨记录 → 导出 → 验证类型过滤正确

## 8. 调拨模块 — 回收类型测试 (Transfer/recovery)

- [x] 8.1 测试回收模板下载：`GET /api/transfers/template?type=recovery` → 验证表头包含回收分类、单位、出库日期、存放位置、资产类目、物品分类
- [x] 8.2 测试回收批量导入完整字段：上传回收数据 → 逐一验证回收分类/单位/出库日期/存放位置/资产类目/物品分类/采购经办人字段正确入库
- [x] 8.3 测试回收导出：创建回收记录 → 导出 → 验证 Excel 仅含回收类型数据

## 9. 盘点模块导入/模板测试 (Inventory)

- [x] 9.1 测试盘点模板下载：创建盘点任务 → `GET /api/inventories/{id}/import-template` → 验证返回 200 + Excel 格式
- [x] 9.2 测试盘点结果导入：创建进行中的盘点任务 → 上传盘点结果 → 验证盘点项数量和结果更新正确

## 10. 边界条件与回归验证

- [x] 10.1 测试特殊字符导入：数据包含换行符、引号、逗号 → 验证入库后值正确
- [x] 10.2 测试缺少必填列的导入：上传缺少必填列的文件 → 验证返回明确错误
- [x] 10.3 运行全量 pytest 确认所有新增测试通过且无回归
