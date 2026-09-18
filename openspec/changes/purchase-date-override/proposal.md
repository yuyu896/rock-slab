## Why

实例档案的"采购日期"当前为出生单日期的纯派生值（一张采购单一个日期管一批），无法表达"同一批中某台设备实际采购日不同"的个体事实。泉州二分 7 台工作手机需要逐台不同的采购日期（前案 prod-data-fix-qz2-dates 已证实改单据/改入库日期均非正解并回滚）。系统已有完全同构的先例：供应商、规格均为"个体覆盖，空=批次口径"三级链——本变更照抄该模式补齐采购日期的个体表达能力。

## What Changes

- **模型**：`FixedAsset` 新增 `采购日期 = DateField('采购日期（个体覆盖，空=批次口径）', null=True, blank=True)`（migration 0028，仿 0026 供应商/0027 规格）。
- **取数链**：序列化器 `get_采购日期` 与生平 timeline 的 `采购日期` 改为 **① 实例个体覆盖 → ② 出生单调拨日期**；覆盖列空 = 现状行为不变。实例列表/标签 DATE:/生平/导出全部经此链，前端零改动。
- **数据应用**：一次性命令 `prod_data_fix_qz2_purchase_dates` 为泉州二分 7 台实例填覆盖值（-36→2025-07-25、-37→2025-12-05、-38/-39/-44→2025-07-07、-40→2025-05-07、-43→2025-01-06）。
- 铁律 1 合规：批次日期仍在单据（单据事实），个体差异只存该实例（档案事实），两层各一份不重复。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fixed-asset-instance`: 新增「采购日期个体覆盖」要求——三级链取数、覆盖列空即批次口径、全部展示面一致生效

## Impact

- **后端**: `apps/assets/models.py`（+1 字段）、`migrations/0028_fixedasset_purchase_date.py`、`serializers.py`（get_采购日期 链）、`views.py`（timeline 链）、`management/commands/prod_data_fix_qz2_purchase_dates.py`（填充）
- **测试**: 序列化器链/timeline 链/填充命令
- **数据**: 仅 7 台实例的覆盖列有值；其余全系统实例覆盖列为空、显示不变
- 前端/导入/导出模板零改动；含 migration，走常规部署
