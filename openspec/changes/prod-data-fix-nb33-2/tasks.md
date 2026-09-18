## 1. 命令实现

- [x] 1.1 新建 `backend/apps/assets/management/commands/prod_data_fix_nb33_2.py`：派生自 nb33，TARGET_NUMBERS = -35/-43/-72；断言与联动逻辑不变

## 2. 测试

- [x] 2.1 三行各删 1 台后行数量/台账/实例三处同步、他台零波及、对账零差异；dry-run；幂等；后端全量 pytest 通过（753 passed）

## 3. 生产执行

- [x] 3.1 push → 部署；备份 rock_slab_20260918_163527.sql.gz
- [x] 3.2 dry-run 复核（7→6、7→6、22→21，在库 72→69）
- [x] 3.3 `--apply` + 独立对账 exit=0（5421 行零差异）；抽查 3 编号已删、台账 69=实例 69、三行数量 6/6/21；幂等复证全跳过
