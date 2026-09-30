## Why

流转 Excel 导入三个静默错数据缺陷（审计复现确认）：① 数量单元格留空/非数值时 `_qty(default=1)` 静默按 1 建单——导入者无感知；② 小数数量 `int(float(raw))` 静默截断（2.9→2）；③ 防重传指纹为「先 exists 检查、导入完成后才写指纹」的 check-then-act，并发双请求双双通过检查 → 同文件双倍建单。

## What Changes

- 数量解析严格化：空值/非数值/非整数小数一律进**行级 errors**（「数量必须为正整数」），不再默认 1、不再截断；整数数值格（5.0）正常接受——与盘点结果导入的既有语义对齐
- 指纹改**原子占位**：`get_or_create(user, sha1)` 先占位（DB 唯一约束保证并发下只有一个请求拿到 created=True），24h 窗口内已存在即 400；窗外旧指纹刷新时间戳开新窗；删除尾部事后写入
- 行为变化（记录）：导入失败后同内容文件 24h 内重传将被指纹拒绝——修正错误必然修改文件内容（=新指纹），与既有提示「如确需重导请修改文件内容」一致

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `transfer-batch-import`: 新增「导入数量严格解析」与「指纹原子占位」要求

## Impact

- `backend/apps/transfers/views.py`：`_qty` 严格化（采购/领用/调拨三处共用）、指纹段重写
- `backend/tests/`：空数量/小数报错用例、并发占位语义用例（同指纹二次导入 400）
- API 行为变化：空数量行从静默建单变 errors 行；小数从截断变 errors；无迁移
