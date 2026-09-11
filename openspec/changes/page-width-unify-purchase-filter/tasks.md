# 版宽统一 + 采购筛选 — 实施任务

## 1. 版宽统一 1600

- [x] 1.1 PurchaseList/AssignList/TransferList：`.transfer-page` 1400→1600
- [x] 1.2 Inventory：`.inventory-page` 1400→1600；RecoveryLedger：100%→1600

## 2. 采购列表分公司筛选

- [x] 2.1 PurchaseList 筛选区加 BranchFilterSelect（toBranch，allLabel=入库分公司），fetchTransfers 透传（useTransferList 链路已有）
- [x] 2.2 vitest：采购筛选携带 toBranch

## 3. 验证

- [x] 3.1 `npm run build` + vitest 全绿
- [x] 3.2 本地手验：五页版宽一致；采购筛选生效
