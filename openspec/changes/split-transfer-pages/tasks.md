## 1. 共享 Composable

- [x] 1.1 创建 `useTransferList.ts` composable，封装公共逻辑：数据获取（带 type 筛选）、分页、筛选、审批（通过/驳回）、详情查看、导出、批量导入
- [x] 1.2 在 composable 中定义各流转类型的元数据（typeLabel、typeColor、表单字段配置）

## 2. 路由配置

- [x] 2.1 在 `router/index.ts` 中新增 6 个路由：`/transfers/purchase`、`/transfers/assign`、`/transfers/return`、`/transfers/transfer`、`/transfers/repair`、`/transfers/scrap`，各自指向独立页面组件
- [x] 2.2 将原 `/assets/transfer` 路由改为 redirect 到 `/transfers/transfer`

## 3. 侧边栏导航

- [x] 3.1 修改 `MainLayout.vue` navItems，将"调拨记录"替换为"资产流转"分组，包含 6 个子菜单项（采购入库、领用出库、归还、调拨、维修、报废）

## 4. 独立页面组件

- [x] 4.1 创建 `PurchaseList.vue`（采购入库）：使用 useTransferList('purchase')，独立新建表单（资产编号、名称、数量、规格型号、入库分公司）
- [x] 4.2 创建 `AssignList.vue`（领用出库）：使用 useTransferList('assign')，独立新建表单（领用人、所属部门）
- [x] 4.3 创建 `ReturnList.vue`（归还）：使用 useTransferList('return')，独立新建表单
- [x] 4.4 创建 `TransferList.vue`（调拨）：使用 useTransferList('transfer')，独立新建表单（调出/调入分公司、部门、负责人、调拨原因）
- [x] 4.5 创建 `RepairList.vue`（维修）：使用 useTransferList('repair')，独立新建表单（维修原因）
- [x] 4.6 创建 `ScrapList.vue`（报废）：使用 useTransferList('scrap')，独立新建表单（报废原因）

## 5. 清理

- [x] 5.1 删除原 `Transfer.vue`（已被拆分页面替代）
- [ ] 5.2 验证侧边栏导航和各页面功能正常
