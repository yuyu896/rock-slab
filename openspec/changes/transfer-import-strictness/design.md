## Context

`_qty(row, col, default=1)`（views.py）供采购/领用/调拨三段共用；`_num` 取单元格原值。指纹段现状：`exists()` 检查 24h 窗 → 解析建单 → 尾部 `get_or_create` 写指纹。`ImportFingerprint` 有 `(user, sha1)` 唯一约束。

## Goals / Non-Goals

**Goals:** 数量错值显式报错；同文件并发导入只成功一次。

**Non-Goals:** 不做指纹失败回收（修正错误必改内容=新 sha1，回收无必要）；不动表头校验/范围校验。

## Decisions

**1. `_qty` 改严格解析并返回 (值或 None)，错误文本由调用处进 errors。**
空/非数值/非整数小数统一「数量必须为正整数（不支持小数与空值）」；`float.is_integer()` 的整数格收敛为 int。与盘点导入刚定的语义一致，一处口径。

**2. 指纹原子占位：入口 `get_or_create`，窗口判断后行。**
并发双请求 → 唯一约束 + get_or_create 的内部重试保证恰好一个 created=True；另一个读到窗内指纹 → 400。窗外（>24h）旧指纹 `update(created_at=now)` 开新窗（update 原子）。导入中抛错由 DRF 处理为 400，指纹保留——见行为变化。

## Risks / Trade-offs

- [导入失败后同文件重传被拒] — 修错必改内容=新指纹；文案已引导改内容。极端（想原样重试瞬态故障）等 24h 或改一个空白格。
- [errors 行与建单行交错时部分导入] — 既有语义（合法行照常建单、错误行进 errors），不变。

## Migration Plan

纯代码。部署即生效。验证：造空数量/小数行导入 → errors 明确；同文件立即重传 → 指纹 400。
