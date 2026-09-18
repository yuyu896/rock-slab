# 采购日期个体覆盖 — 实施任务

- [x] 1.1 FixedAsset 加 `采购日期` 可空列（migration）；get_采购日期 两级派生；batch-upddate 白名单加 采购日期（单值，入库日期同步写/清除回退）；测试：两级派生/入库日期联动/清空回退/单据不动
- [x] 1.2 编辑弹窗加「采购日期」el-date-picker（空=沿用出生单），提交链路含日期；vitest 适配 + build
- [x] 2.1 全量 pytest + vitest；本地手验后交用户部署
