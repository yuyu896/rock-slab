## Context

Asset 模型使用中文命名字段（`数量`、`当前状态`、`分公司` 等），数量存储在 `Asset.数量`（IntegerField）。资产状态有 5 种：在库、使用中、维修中、已报废、盘点中。

当前流转流程：所有 6 种操作都通过 `_create_action()` 创建 Transfer 记录，但只有 purchase 有后续的 `warehouse()` 确认步骤会更新 Asset。其余 5 种操作在 `approve()` 审批通过后只修改 Transfer 的 `审批状态`，**不触碰 Asset 表**。

Asset ViewSet 是 ReadOnlyModelViewSet，设计意图是"资产信息通过流转模块自动更新"，但实际只有 purchase 做到了。

## Goals / Non-Goals

**Goals:**
- 领用/归还/调拨审批通过后，自动更新对应 Asset 的状态和归属字段
- 删除维修(repair)和报废(scrap)功能的前后端代码
- Category 计数使用 `Sum('数量')` 统计总数量
- 保持与现有 purchase warehouse 流程的一致性

**Non-Goals:**
- 不改变现有的审批流程（待审批→已通过→已入库）
- 不增加新的流转操作类型
- 不重构 Transfer 模型
- 不处理历史数据修复（单独处理）

## Decisions

### 1. 在 approve() 中根据 action_type 执行 Asset 更新

在现有 `approve()` 方法中，审批通过后根据 `action_type` 调用对应的 Asset 更新逻辑。不再为每种操作增加类似 warehouse 的二次确认步骤。

**理由**: 采购需要二次确认（warehouse）是因为实际入库操作与审批有时间差。其他操作（领用、调拨等）审批通过即视为操作完成，无需二次确认。

### 2. 删除维修/报废功能

从 Transfer 模型的 `ACTION_TYPE_CHOICES`、ViewSet 的 action 端点、前端常量和 UI 中移除 repair 和 scrap。

**理由**: 业务上不需要维修和报废流程，保留只会增加维护成本和用户困惑。

**影响范围**: 后端 models、views、serializers；前端 constants、types、流转页面。已有的 repair/scrap 类型 Transfer 记录保留在数据库中不受影响（历史数据不动）。

### 3. 按 Asset 编号匹配 Asset 记录

流转操作通过 Transfer 记录中的 `资产编号` 找到对应的 Asset 行，然后更新。使用 `select_for_update()` 防止并发问题。

### 4. Category 计数字段拆分

将 `asset_count` 改为按实际含义统计：
- `asset_count` → 资产种类数（Asset 行数，即 `.count()`，保持不变）
- 新增 `asset_total_quantity` → 资产总数量（`Sum('数量')`）
- `in_stock_count` → 在库种类数（保持 `.count()` 含义）
- 新增 `in_stock_quantity` → 在库总数量（`Sum('数量')` where 在库）

**理由**: 前端可能需要展示"种类数"和"总数量"两个维度。

## Risks / Trade-offs

- **[审批即生效，不可撤销]** → 审批通过后立即更新 Asset，如果误审批需要"反向操作"恢复。
- **[现有不一致数据]** → 已审批的 Transfer 记录可能已经造成 Asset 状态与实际不符。需提供数据修复脚本，但不在此变更范围内。
- **[并发安全]** → 使用 `select_for_update()` + `transaction.atomic()` 保证同一 Asset 不会同时被多个操作修改。
- **[删除维修/报废后状态选项减少]** → Asset 状态中"维修中"和"已报废"将不再有代码路径设置，可保留为枚举值（不影响）或一并清理。
