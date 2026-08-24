# asset-freeze-readonly Specification（修改）

## REMOVED Requirements

### Requirement: Asset 写接口冻结
**Reason**: Asset 表整体物理退役（P2 第三刀，决策 #4）：模型、数据表、ViewSet、序列化器全部删除，`/api/assets/` 主路由下线。冻结使命（P1→P2 过渡期保留历史视图）已完成，台账/字典/单据承载全部事实且对账零差异。
**Migration**: 前端资产明细页与移动端资产查询已全部切换台账/实例口径；`/api/assets/` 请求返回 404（summary/fixed-assets 子路由不受影响）；历史数据不可再经 API 查询（事实由台账与单据流水承载）。

### Requirement: 流转审批不再写 Asset
**Reason**: Asset 表已不存在，联动唯一承接方为台账 + 实例（document-ledger-sync / document-instance-binding）。
**Migration**: 无存量动作；该约束由「表不存在」结构性保证。

### Requirement: 盘点降级为记录模式
**Reason**: 盘点明细已改挂台账行（见 inventory-item-basis），「不改 Asset」的约束对象消失；记录模式语义并入新能力（差异修数走调整单，P3 接自动生成）。
**Migration**: 盘点行为不变（记录模式），约束文本移入 inventory-item-basis。

### Requirement: 报表切换台账口径
**Reason**: 报表自 P1 起已从台账取数（report-data-scoping），Asset 退役后「不依赖 Asset」自动成立，约束失去对象。
**Migration**: 无存量动作；报表口径由 report-data-scoping 持续约束。
