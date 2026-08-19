## Context

- 侧边栏由 `frontend/src/components/layout/SidebarNav.vue` 自绘（非 el-menu）：`expandedMenu = ref<string | null>` 单值互斥——展开「资产流转」会把「库存」收起，这是本次要修的交互问题。
- 「库存」子菜单当前有两项：资产列表（`/assets/list`，`views/AssetList.vue`，页面标题「资产列表」）和固定资产表。
- `Asset` 模型有 `branch` 外键（关联 `Branch`）及冗余的 `分公司`/`分公司编号` 字符串字段；报表模块 `apps/reports/views.py` 已有 `_scope_queryset`（基于 `resolve_user_scope` 的统一管理授权过滤，`branch_field='branch'`），是数据隔离的成熟范式。

## Goals / Non-Goals

**Goals:**
- 菜单与页面文案统一为「资产明细」，路由 `/assets/list` 不变。
- 「库存」最上方新增「资产汇总」页（`/assets/summary`），按分公司汇总资产编号（模板版：分公司名/编码、资产总数、编号起止）。
- 侧边栏允许多个子菜单同时展开，再点一次才收起。

**Non-Goals:**
- 不改路由路径、权限模型、数据库结构（无迁移）。
- 资产汇总的最终维度（按状态/类目拆分、编号段明细等）不在本次范围——先交模板，用户后续专门调整。
- 不动移动端布局（MobileLayout 无该下拉交互）。

## Decisions

### D1. 重命名只改文案，不改路由
**选择**：菜单 label、`router/index.ts` 的 `meta.title`、页面 `<h1>`、导出文件名前缀改为「资产明细」；`/assets/list` 路径保留。
**理由**：改路径会破坏已有书签、角色权限里的路径引用（如有）并引入无谓的兼容代码；文案与路径解耦是最低成本方案。

### D2. 汇总接口放 `apps/assets`，函数视图
**选择**：`GET /api/assets/summary/`，在 `apps/assets/views.py` 新增 `@api_view(['GET'])` 函数视图（挂 `urlpatterns` 前部，避免被 `DefaultRouter` 的 `r''` 吞掉）；聚合 `Asset` 按 `branch` 分组：`values('branch__name', 'branch__code').annotate(total=Count('id'), min_code=Min('资产编号'), max_code=Max('资产编号'))`，按 `branch__code` 排序。
**备选**：放 `apps/reports`（`/api/reports/asset-summary/`）。未选：编号汇总属于资产域而非报表域，且 reports 全是报表页面用的统计接口。
**数据隔离**：从 `apps.reports.views` 导入 `_scope_queryset` 复用（同一套授权语义，避免两份实现漂移）；若嫌跨 app 引用私有函数，可顺手把它挪到 `apps/permissions/scope.py`——倾向直接 import，最小改动。

### D3. `expandedMenu` 单值改集合
**选择**：`expandedMenu: Ref<string|null>` → `expandedMenus: Ref<Set<string>>`；`toggleDropdown` 切换集合内有无；模板判断 `expandedMenus.has(item.path)`。收起侧边栏（collapsed）时清空集合，避免展开后折叠再展开的残留。
**理由**：自绘菜单没有现成的 `unique-opened` 开关，改数据结构即是最小修法；不引入 el-menu 重写。

### D4. 资产汇总页为纯展示模板
**选择**：`views/assets/AssetSummary.vue`，纯 CSS 表格（与 AssetList 风格一致），列：分公司、编码、资产总数、编号起始、编号截止；底部合计行；无筛选无分页（分公司数量有限）。
**理由**：用户明确定位为「先做模板、后续专门修改」，最小可改结构。

## Risks / Trade-offs

- [汇总接口被 `DefaultRouter(r'')` 路由遮蔽] → 在 `urls.py` 用 `path('summary', ...)` 显式排在 router.urls 之前。
- [`资产编号` 为字符串，Min/Max 是字典序而非数值序] → 模板阶段接受字典序（编号规则一致时即等价数值序）；若后续编号格式混杂，在专门调整时再处理。
- [无授权用户看到空表] → 与报表行为一致（返回空数组），非 bug。
- [多展开后侧栏变长] → `.sidebar-nav` 已有 `overflow-y: auto`，可接受。

## Migration Plan

纯前后端代码变更，无迁移。部署走 `deploy.sh`（collectstatic + 前端 build）。回滚即 git revert。

## Open Questions

（无——汇总维度已确认先出模板，后续专门调整。）
