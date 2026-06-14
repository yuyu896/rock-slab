## Why

当前系统中，资产流转（领用、归还、调拨、维修、报废）只创建了 Transfer 日志记录，**从未更新 Asset 表的数量和状态**。只有采购入库的 warehouse 确认步骤会修改 Asset。导致资产数量和状态与实际业务严重脱节——领用了资产状态仍显示"在库"，报废了数量不变。此外，Category 的资产计数用的是行数 `.count()` 而非 `Sum('数量')`，当单条 Asset 数量>1 时计数错误。

## What Changes

- 领用(assign)审批通过后：Asset 状态从"在库"改为"使用中"，更新使用人、所属部门等字段
- 归还(return)审批通过后：Asset 状态改回"在库"，清空使用人
- 调拨(transfer)审批通过后：Asset 的分公司/所属区域字段更新为目标分公司
- **删除维修(repair)和报废(scrap)功能** — 前后端代码全部移除
- Category 计数从 `.count()` 改为 `Sum('数量')` + `Count`，区分资产种类数和资产总数量

## Capabilities

### New Capabilities
- `transfer-asset-sync`: 资产流转操作（领用/归还/调拨）审批通过后自动同步更新 Asset 表的状态和归属字段
- `remove-repair-scrap`: 删除维修和报废功能的前后端代码
- `category-quantity-count`: Category 资产计数使用 Sum('数量') 统计总数量而非行数

### Modified Capabilities

## Impact

- **后端**: `transfers/views.py` — approve 方法需根据 action_type 执行对应的 Asset 更新逻辑
- **后端**: `categories/signals.py` — 计数逻辑从 count 改为 Sum
- **后端**: `categories/models.py` — 可能需要新增字段区分"资产种类数"和"资产总数量"
- **前端**: 可能受影响 — 资产列表状态筛选、分类页面的计数展示
- **现有数据**: 需要检查现有已审批的 Transfer 记录是否已造成数据不一致，提供修复方案
