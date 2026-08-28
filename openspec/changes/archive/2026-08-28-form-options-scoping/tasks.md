## 1. 后端：分公司范围参数与台账正数列筛选

- [x] 1.1 `BranchViewSet.get_queryset`：`scope=write` 时按 `resolve_user_scope` 过滤（all→不过滤，否则 `id__in=scope.branches`），无参全量不变
- [x] 1.2 `AssetStockFilterSet` 加 `positive_column` 筛选（ChoiceFilter：在库数量/在用数量/回收库数量，该列>0）
- [x] 1.3 pytest：branches scope=write 四场景（范围受限/admin/无参全量/无授权空列表）+ positive_column 过滤与非法值

## 2. 前端：ItemPicker 双数据源

- [x] 2.1 `api/branches.ts` 加 `scope` 参数；`api/assets.ts` 的 `getAssetStocks` 参数类型加 `positive_column`
- [x] 2.2 `ItemPicker` 加 `branch`/`stockColumn`/排除消耗品 props：有 stockColumn 走台账检索（选项行显示可用数量），branch 为空禁用提示"请先选择分公司"；无 stockColumn 维持字典检索
- [x] 2.3 `TransferLinesEditor` 内计算扣数列映射（assign+stock→在库 / assign+recycle_bin→回收库+剔消耗品 / transfer→在库 / recovery→在用 / purchase→无）传给每行 ItemPicker
- [x] 2.4 vitest：ItemPicker 双数据源分支、未选分公司禁用、回收库剔除消耗品

## 3. 前端：写单页分公司下拉收口

- [x] 3.1 PurchaseCreate / AssignCreate / RecoveryCreate（PC）与 MobilePurchase / MobileAssign（移动）：扣数/入库分公司下拉换 `getBranches({ scope: 'write' })`
- [x] 3.2 TransferCreate（PC）与 MobileTransfer：调出=scope=write、调入=无参全量，两份选项拆分
- [x] 3.3 确认既有 `getBranches()` 调用方（筛选/组织/权限/盘点创建页）不受影响（无参行为未变，跑相关 vitest）

## 4. 验证与收尾

- [x] 4.1 后端 `pytest` 全绿（含对账命令测试）；前端 `npm run build` + `vitest` 全绿
- [x] 4.2 本地起服实测：范围受限账号在四页验证下拉收口与品目过滤，admin 验证全量；核对调拨调入全量
- [x] 4.3 更新 `docs/design/v2-revision-draft.md` 拆案表第 9 案状态；feat + openspec 两个 commit → push
