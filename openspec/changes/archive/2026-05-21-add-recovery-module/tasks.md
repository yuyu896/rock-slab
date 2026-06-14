## 1. 后端模型与迁移

- [x] 1.1 在 `backend/apps/transfers/models.py` 的 ACTION_CHOICES 中新增 `recovery` 类型
- [x] 1.2 在 Transfer 模型上新增字段：`回收分类`、`单位`、`出库日期`、`存放位置`、`资产类目`、`物品分类`
- [x] 1.3 新增 RECOVERY_CATEGORY_CHOICES（闲置回收、报废回收、捐赠回收、其他）
- [x] 1.4 生成并检查数据库迁移文件

## 2. 后端 API 适配

- [x] 2.1 更新序列化器，确保回收专用字段在 recovery 类型时可读写
- [x] 2.2 确认 `getTransfers` 接口的 `action_type=recovery` 筛选正常工作
- [x] 2.3 确认导入/导出接口支持 recovery 类型

## 3. 前端路由与导航

- [x] 3.1 在 `frontend/src/router/index.ts` 中新增 `/transfers/recovery` 路由，指向 `RecoveryList.vue`
- [x] 3.2 在 `SidebarNav.vue` 资产流转分组中新增"回收"菜单项
- [x] 3.3 在 `useTransferList.ts` 的 TRANSFER_TYPES 中新增 `recovery` 类型元数据

## 4. 前端回收列表页

- [x] 4.1 创建 `frontend/src/views/transfers/RecoveryList.vue`
- [x] 4.2 表格按用户要求顺序显示 17 列：序号、分公司、资产编号、资产类目、物品分类、资产名称、回收分类、入库日期、数量、单位、规格、出库日期、所属部门、当前处理状态、存放位置、经办人、备注
- [x] 4.3 实现筛选（状态、分公司、关键词）和分页
- [x] 4.4 实现新建回收记录弹窗（含回收分类下拉选项）
- [x] 4.5 实现详情查看弹窗
- [x] 4.6 实现导出功能

## 5. 验证

- [x] 5.1 启动后端，运行迁移，确认 recovery 类型可正常创建 Transfer 记录
- [x] 5.2 启动前端，访问回收页面，确认列表、筛选、新建、详情、导出功能正常
