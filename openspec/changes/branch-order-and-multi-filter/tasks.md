## 1. 后端

- [x] 1.1 流转列表统一排序：TransferViewSet 列表查询集注记状态序（Case 待审批→0/草稿→1/其余→2）→ `-调拨日期` → `-created_at`（五类型一致；等值比较无中文 collation 依赖）
- [x] 1.2 分公司过滤多值化：transfers filters（调入/调出分公司名称）、资产（分公司编号）、盘点（branch id）、调整记录等各过滤参数改逗号切分→`__in`；逐个核对既有 filterset 字段口径
- [x] 1.3 后端测试：多选筛选命中（两公司并集/空=全部）、排序断言（待审批置顶跨页、同组日期倒序、草稿第二）；branch-filter 既有用例回归（命中语义不变）

## 2. 前端

- [x] 2.1 新增共享工具 `sortBranchesByName`（localeCompare zh）；BranchFilterSelect 内部对 options 排序
- [x] 2.2 BranchFilterSelect 改多选：ElSelect multiple + collapse-tags，值 `string[]`（[]=全部），去「全部分司」哨兵项
- [x] 2.3 消费页多值透传（grep 清点 9 页）：流转四页走 useTransferList 一处改（filters.branch → string[]，请求 join(',')）；资产台账/实例档案/盘点任务/回收台账/调整记录页逐页改并核对字段口径
- [x] 2.4 创建页分公司下拉（采购/领用/调拨/回收）按名称拼音排序；组织架构树分公司节点同序
- [x] 2.5 PurchaseList 删页内 `sortedTransfers` 重排，直接渲染服务端序
- [x] 2.6 前端用例更新：多选筛选参数、排序工具、列表直渲

## 3. 验证收尾

- [x] 3.1 后端 pytest 全量 + 前端 vitest + `npm run build` 全绿
- [x] 3.2 拆 feat + openspec 两 commit，push
- [ ] 3.3 手验：下拉拼音序、多选两家并集筛选、翻页待审批置顶、组织树分公司序
- [ ] 3.4 生产部署（用户自行），线上抽查同 3.3
