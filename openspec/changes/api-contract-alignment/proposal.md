## Why

中风险第一批（契约对齐三件套），全部为静默失效类缺陷——不报错但功能形同虚设：① 后端响应键经 camelize 输出为 `actionType`，前端 5 个文件 8 处仍读 `action_type`（类型显示降级、领用「库存来源」行永不渲染）；② 通知「加载更多」不传页码且新数据被丢弃（永远第一页）、「仅未读」与审计四项筛选发 camelCase 查询参数而后端 filterset 只认 snake_case（**查询串不经 camel-case parser 转换**，全部静默失效）；③ 移动端「今日操作」传 `createdAt__gte`，transfers 过滤器未声明该字段，统计成全量单据数。

## What Changes

- 前端 8 处 `action_type` 读取改 `actionType`（types/index.ts 类型声明 + Dashboard + 移动审批列表/详情 + 单据详情布局）
- 通知分页：store 透传 `page/pageSize`、组件「加载更多」翻页并**追加**（原来丢弃）；`isRead` 请求参数在边界翻译为 `is_read`
- 审计页参数构造改为显式 snake_case 映射（`resource_type/is_success/start_date/end_date`），不再整体展开 camelCase filters
- TransferFilterSet 声明 `createdAtGte`（与 fromBranch 同款 camel 命名约定），移动端「今日操作」改传该参数——统计口径回归「今日创建」

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `frontend-contract-alignment`: 新增「响应键 camelCase 契约（actionType）」「查询参数命名与通知分页」「流转创建时间过滤」三项要求

## Impact

- `frontend/src/types/index.ts`、`views/Dashboard.vue`、`views/mobile/ApprovalList.vue`、`views/mobile/ApprovalDetail.vue`、`views/transfers/components/TransferDetailLayout.vue`
- `frontend/src/store/notification.ts`、`views/mobile/NotificationList.vue`、`views/AuditLog.vue`、`views/mobile/Home.vue`
- `backend/apps/transfers/filters.py`（+createdAtGte）
- 后端新增过滤用例；前端 vitest + `npm run build` 过关
- 无迁移；响应结构不变（只修读取侧）
