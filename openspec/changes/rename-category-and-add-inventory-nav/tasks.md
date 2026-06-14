## 1. 侧边栏 — 品目改名

- [x] 1.1 `SidebarNav.vue`：将「资产分类」菜单 label 改为「品目」
- [x] 1.2 `Category.vue`：页面标题从「资产分类」改为「品目」

## 2. 侧边栏 — 库存分组

- [x] 2.1 `SidebarNav.vue`：新增「库存」一级分组（可展开），将「资产列表」从顶层移入其下
- [x] 2.2 `SidebarNav.vue`：在库存分组下新增「固定资产表」子菜单项，路径 `/fixed-assets`

## 3. 固定资产表页面

- [x] 3.1 `router/index.ts`：新增 `/fixed-assets` 路由，指向 `FixedAssetList.vue`
- [x] 3.2 新建 `views/FixedAssetList.vue`：复用 getAssets API，默认筛选 `category=固定`，包含分公司/状态/关键词筛选和分页
