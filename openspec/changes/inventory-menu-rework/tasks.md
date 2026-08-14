## 1. 后端：资产汇总接口

- [x] 1.1 `apps/assets/views.py` 新增 `summary` 函数视图（`GET`）：复用 `apps.reports.views._scope_queryset` 隔离，按 `branch` 聚合 `total/min(资产编号)/max(资产编号)`，按分公司编码排序；`apps/assets/urls.py` 显式注册 `summary` 路由（排在 `router.urls` 之前）
- [x] 1.2 后端测试：admin 见全集、按授权范围过滤、无授权返回空数组（`backend/tests/`）

## 2. 前端：资产汇总页

- [x] 2.1 `api/assets.ts` 新增 `getAssetSummary`；`types/` 新增汇总行类型
- [x] 2.2 新增 `views/assets/AssetSummary.vue`：标题「资产汇总」，表格列（分公司、编码、资产总数、编号起始、编号截止）+ 合计行；空数据展示
- [x] 2.3 `router/index.ts` 注册 `assets/summary` 路由（`meta.title: '资产汇总'`）

## 3. 前端：菜单与文案

- [x] 3.1 `SidebarNav.vue`：「库存」子菜单最上方插入「资产汇总」（`/assets/summary`）；「资产列表」label 改「资产明细」
- [x] 3.2 `SidebarNav.vue`：`expandedMenu` 单值改为 `expandedMenus: Set<string>`，支持多分组同时展开、再点收起自身
- [x] 3.3 `AssetList.vue` 页面标题及导出文件名前缀改「资产明细」；`router/index.ts` 的 `/assets/list` `meta.title` 改「资产明细」（路径不变）

## 4. 测试与部署

- [x] 4.1 后端 `pytest` 全绿；前端 `npm run build` + `npm run test` 全绿
- [x] 4.2 手动验证：库存子菜单顺序与命名、多分组同时展开、资产汇总页数据与授权隔离
- [x] 4.3 部署 `deploy.sh` 并线上验证
