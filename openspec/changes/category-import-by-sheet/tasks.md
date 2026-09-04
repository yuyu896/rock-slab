## 1. 后端多 sheet 导入

- [x] 1.1 import_excel 改造：遍历全部 sheet，表名精确映射 {数量管理→quantity, 实例管理→instance, 消耗品→consumable}；无命中回退 active sheet + quantity（结果明示）；按 sheet 分组统计（name/management_type/imported/errors），外层保留 imported/errors 兼容；未命中表名列 skipped
- [x] 1.2 存量守卫：update_or_create 前查已有品目，管理方式变化且 management_stock_status 锁定 → 行级错误跳过
- [x] 1.3 行数上限改为命中 sheet 行数合计（validate_row_count 口径调整）
- [x] 1.4 后端回归：三表导入各落正确管理方式 / 回退兼容 / 存量守卫跳过 / skipped 清单

## 2. 前端模板与弹窗

- [x] 2.1 generateCategoryTemplate 改为三 sheet（数量管理/实例管理/消耗品）同表头；vitest 校验三 sheet 名
- [x] 2.2 CategoryImportDialog 文案说明 sheet 命名规则；结果展示按 sheet 分组条数与 skipped 提示

## 3. 测试与验收

- [x] 3.1 后端 pytest 全量 + 前端 vitest 全量 + `npm run build` 类型门
- [x] 3.2 本地实测：真实「资产分类清单.xlsx」导入（405 行三表），品目页按管理方式筛选核对各档条数与编号；旧单 sheet 文件回归
- [x] 3.3 生产导入正式清单并核对（品目现为 0 条，全量 create；对账命令通过）
