# 品目导入按 sheet 名定管理方式 — 设计

## Context

现导入实现（`apps/categories/views.py` import_excel）：只读 `wb.active`，7 列契约（资产类目/物品分类/资产名称/资产编号/计量单位/警戒线/备注），按 `asset_code` update_or_create 幂等，管理方式恒缺省 quantity。存量守卫在 serializer 层（`management_stock_status`：挂实例档案或台账三列任一非零即锁定管理方式）。前端模板 `generateCategoryTemplate` 生成单 sheet「资产分类」。正式清单三张 sheet 表头与契约一致，仅按 sheet 名区分管理方式。

## Goals / Non-Goals

**Goals:**
- 同一个 xlsx 文件一次导入，三张 sheet 各自落到正确管理方式
- 旧单 sheet 文件不破坏（回退 active sheet + quantity）
- 不给「管理方式切换须无存量」守卫开后门

**Non-Goals:**
- 不加管理方式列解析（sheet 名是唯一来源；表内若有该列也忽略）
- 不做 sheet 顺序要求、不做跨 sheet 编号冲突的特殊处理（同一编号出现在多张 sheet = 后一张覆盖前一张，沿用 update_or_create 语义并在结果中不加特殊提示）
- 不改导出

## Decisions

1. **sheet 名精确匹配映射**：`{'数量管理': 'quantity', '实例管理': 'instance', '消耗品': 'consumable'}`，键值与 `MANAGEMENT_TYPE_LABELS`（前端）及模型 choices（后端）同源。精确匹配（不去空格、不模糊），命名错一张只影响那一张并在结果里列出，不整单失败。
2. **回退而非报错**：全簿无命中 sheet 时按现状读 active sheet 以 quantity 导入。理由：既有用户手里的是单 sheet 文件，报错会把他们挡在门外；回退保留完全兼容，代价是 sheet 名打错时静默落到数量管理——用结果信息（「未识别命名的 sheet，按数量管理导入」）兜底提示。
3. **存量守卫逐行执行**：update_or_create 前查已有品目；管理方式不同且 `management_stock_status()` 锁定 → 该行计入 errors 跳过。判定函数复用 serializer 层现成实现，不在导入里重写第二份（铁律 1：一处事实）。
4. **行数上限按全簿合计**：`validate_row_count` 现按单 ws 计；多 sheet 后改为命中 sheet 行数合计（防拆 sheet 绕限），上限值不变。
5. **响应结构**：`{imported, sheets: [{name, management_type, imported, errors: [...]}], skipped_sheets: [...], errors: [...]}`——外层 errors 保留兼容现有前端展示，sheets 供弹窗分组展示。

## Risks / Trade-offs

- [sheet 名打错静默按数量管理] → 结果信息明示回退行为与未识别 sheet 名清单，弹窗直接展示
- [同编号跨 sheet 重复，后者覆盖前者] → 语义与现状一致（update_or_create）；导入结果按 sheet 列出条数，用户可核对
- [旧文件回退路径与多 sheet 路径行为分叉] → 回退路径就是原逻辑原样保留，测试双覆盖

## Migration Plan

纯代码变更，无迁移。部署后直接在品目页导入「资产分类清单.xlsx」验收；失败可整批按编号重导（幂等）。
