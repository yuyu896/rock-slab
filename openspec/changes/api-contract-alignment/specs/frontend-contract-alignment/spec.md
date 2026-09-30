## ADDED Requirements

### Requirement: 流转数据读取必须使用 camelCase 响应键

后端响应键经 camelize 渲染器输出为 camelCase，前端读取流转单据的类型字段 MUST 使用 `actionType`（不得读取 `action_type`）：TypeScript 类型声明（`Transfer.actionType`）、仪表盘待办/动态类型展示、移动端审批列表/详情的类型标签、单据详情布局的类型分支（如领用单「库存来源」行的 `actionType === 'assign'` 判定）均在此列。

#### Scenario: 移动端审批类型正确显示

- **WHEN** 用户打开移动端审批中心，列表含采购/领用/调拨单
- **THEN** 每单的类型标签显示真实类型（不再是兜底的「调拨」）

#### Scenario: 领用详情显示库存来源

- **WHEN** 打开带领用来源（新品库/回收库）的领用单详情
- **THEN** 「库存来源」行正常渲染

### Requirement: 查询参数必须按后端过滤器声明命名且通知分页有效

URL 查询串不经请求体 parser 转换（架构事实），前端查询参数 MUST 与后端 FilterSet 声明的名字一致：通知筛选传 `is_read`、审计筛选传 `resource_type/is_success/start_date/end_date`（ camel→snake 的翻译收敛在 store/API 边界层，组件层保持 camel 语义）。通知「加载更多」MUST 递增 `page` 参数并**追加**结果到既有列表（不得丢弃或整体覆盖），首页加载重置 `page=1`；分页以 `page/pageSize` 与 StandardPagination 对齐。

#### Scenario: 仅未读筛选生效

- **WHEN** 用户在通知页开启「仅未读」
- **THEN** 列表只含未读通知（后端 is_read=false 过滤生效）

#### Scenario: 加载更多翻页追加

- **WHEN** 通知列表超过一页且用户点击「加载更多」
- **THEN** 请求携带下一页码，返回数据追加在列表尾部（不再重复第一页）

#### Scenario: 审计筛选生效

- **WHEN** 审计页选择资源类型/状态
- **THEN** 列表按所选条件过滤（后端 snake_case 过滤器命中）

### Requirement: 流转列表支持创建时间过滤（今日操作口径）

TransferFilterSet MUST 声明 `createdAtGte` 过滤器（`created_at` 的 `gte`，camel 命名与 fromBranch/toBranch 同族）；移动端「今日操作」统计 MUST 以 `createdAtGte=当日零点` 查询，口径为**当日创建的单据数**。

#### Scenario: 今日操作只计当日

- **WHEN** 移动端首页加载「今日操作」卡片
- **THEN** 数字为今日创建的流转单据数（历史单据不计入）
