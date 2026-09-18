## 1. 命令实现

- [x] 1.1 新建 `backend/apps/assets/management/commands/prod_data_fix_bj3_point.py`：点删 + 归零删行空行删单；断言沿用 nb33 体系；幂等；内嵌对账复验

## 2. 测试

- [x] 2.1 功能：单实例行单据删行删单、台账镜像同步、他台他司零波及、对账零差异；多行单据仅删目标行；dry-run；幂等；后端全量 pytest 通过（757 passed）

## 3. 生产执行

- [ ] 3.1 push → 部署；备份
- [ ] 3.2 dry-run 复核（删 CG20260806-023、台账 49→48）
- [ ] 3.3 `--apply` + 独立对账 exit=0；抽查编号已删、48=48、单据不存在；幂等复证
