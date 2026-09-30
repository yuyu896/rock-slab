## Context

后端 REST 配置 `CamelCaseJSONRenderer/Parser`：**请求体/响应体**键名双向转换，但 **URL 查询串不经 parser**、原样进入 filterset——因此响应侧前端读 camelCase 是对的（`item.isRead` ✓），请求查询参数必须手写后端声明的名字（`isRead` ✗ / `is_read` ✓）。TransferFilterSet 现有自定义过滤器用 camel 命名（fromBranch/toBranch）。通知分页走 StandardPagination（page/pageSize）。

## Goals / Non-Goals

**Goals:**

- actionType 读取侧全量对齐（含类型声明），显示恢复设计语义
- 通知筛选生效、「加载更多」真翻页真追加
- 审计四项筛选生效
- 「今日操作」= 今日创建的单据数

**Non-Goals:**

- 不做后端查询参数的 camelCase 兼容层（正确方向是前端按后端声明发参；parser 只管 body 是既有架构事实）
- 不改通知/审计的响应结构
- 不重做通知列表 UI

## Decisions

**1. actionType：只改读取侧 8 处（含 types 声明），不动后端。**
响应键现状即 `actionType`（渲染器全局行为、多数页面已正确读取），改前端是唯一正确方向。

**2. 通知参数翻译放 store 边界：组件/调用方继续用 `isRead` 语义，store 调 API 前译成 `is_read` 并透传 `page/pageSize`。**
store 是该 API 的唯一调用边界，翻译集中一处；组件保持可读的 camel 语义。

**3. 加载更多语义：page 从 1 起，loadMore 时 `page=当前+1`，结果追加；`hasMore = 本页条数 >= pageSize`。**
原实现的 `currentPage` 递增了但没进请求——补上即活。翻页后回到顶部刷新重置 page=1。

**4. 审计页放弃 `...filters.value` 整体展开，显式构造 snake 参数。**
展开会把 dateRange 数组与 camel 键一并发给后端；显式映射 `action/resource_type/is_success/search/start_date/end_date` 一眼可查。

**5. 后端 `createdAtGte = DateTimeFilter(field_name='created_at', lookup_expr='gte')`，前端 Home 改传 `createdAtGte`。**
跟 filterset 既有的 camel 命名族（fromBranch/toBranch）一致，而不是 django-filter 的 `字段__查找式` 风格——后者会把任意 created_at 过滤面暴露成通用参数族，前者是显式单点声明。

## Risks / Trade-offs

- [actionType 改动碰 5 个文件，可能有测试锚定旧键] — vitest 全跑 + vue-tsc 兜底，逐个修锚
- [hasMore 以页满判定，末页恰好等于 pageSize 时多一次空加载] — 空结果追加无副作用，且下次 hasMore 归零；简单性优先

## Migration Plan

纯代码。部署即生效。验证：Dashboard 待办类型正确显示；移动审批类型正确；领用详情出现「库存来源」行（有领用来源时）；通知「仅未读」生效、加载更多出新数据；审计筛选生效；移动端「今日操作」数字变小（=当日单据数）。
