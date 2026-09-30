## 1. 前端

- [x] 1.1 `types/index.ts` Transfer 声明 `action_type`→`actionType`；Dashboard/移动审批列表/详情/单据详情布局共 8 处读取对齐
- [x] 1.2 `store/notification.ts`：fetchNotifications 透传 `page/pageSize`、边界翻译 `isRead→is_read`；`NotificationList.vue` 加载更多翻页+追加、首页重置
- [x] 1.3 `AuditLog.vue`：参数显式 snake 映射（action/resource_type/is_success/search/start_date/end_date）
- [x] 1.4 `mobile/Home.vue`：今日操作改传 `createdAtGte`

## 2. 后端

- [x] 2.1 `transfers/filters.py` 声明 `createdAtGte`；新增过滤用例（当日/昨日单据）

## 3. 验证

- [x] 3.1 vitest 全跑 + `npm run build`（类型门禁）+ 后端全量 `pytest`
- [ ] 3.2 手验要点记录（类型显示/仅未读/加载更多/审计筛选/今日操作数字）

> 手验要点：Dashboard 待办/动态显示真实类型；移动审批类型标签正确；带领用来源的领用详情出现「库存来源」行；通知「仅未读」生效、「加载更多」出新页数据；审计页筛选生效；移动端「今日操作」=当日单据数。
