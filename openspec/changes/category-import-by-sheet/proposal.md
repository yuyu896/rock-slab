# 品目导入按 sheet 名定管理方式

## Why

正式品目清单（资产分类清单.xlsx）按管理方式分成三张工作表——「数量管理」（约 339 条）、「实例管理」（约 7 条）、「消耗品」（约 59 条），表头同现有 7 列导入契约但**没有管理方式列**。现有导入只读第一张 active sheet 且一律按数量管理入库，这份文件无法直接导入：要么拆文件，要么手工逐条改管理方式。

## What Changes

- 品目 Excel 导入升级为多 sheet：工作表名精确匹配「数量管理 / 实例管理 / 消耗品」即按对应管理方式导入该 sheet 全部行；三张可同文件一次导入
- 整个工作簿无任何命中命名的 sheet 时，回退现有行为（active sheet 按「数量管理」导入），兼容既有单 sheet 文件
- 导入更新已存在品目时若要变更管理方式且该品目有存量（挂实例档案或台账任一数量列非零），该行 MUST 报错跳过（不得绕过「管理方式切换须无存量」守卫）
- 导入结果按 sheet 分组返回（每张 sheet 的导入条数与所用管理方式）；未命中的 sheet 名列出提示
- 前端导入模板改为三张 sheet（数量管理/实例管理/消耗品）各带同一 7 列表头；导入弹窗文案说明 sheet 命名规则

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `item-dictionary`: 新增需求「品目 Excel 导入按 sheet 名定管理方式」——多 sheet 识别规则、回退兼容、存量守卫、结果分组与模板三 sheet 化

## Impact

- 后端：`backend/apps/categories/views.py`（import_excel 多 sheet 遍历、sheet 名映射、逐行守卫）；行数校验口径从单 sheet 调整为全簿合计
- 前端：`frontend/src/utils/importTemplate.ts`（generateCategoryTemplate 三 sheet）、`CategoryImportDialog.vue`（文案与结果展示）
- 测试：后端导入多 sheet/回退/守卫回归；前端模板 vitest；类型门 `npm run build`
- 铁律不涉：导入只写字典属性，零台账数量变动；生产品目现为 0 条，首轮导入全部走 create
