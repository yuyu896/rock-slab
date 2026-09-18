## 1. 纠错命令实现

- [x] 1.1 新建 `backend/apps/assets/management/commands/prod_data_fix_bj_serials.py`：常量固化（北京三分/五分 × A-a00011），`--apply` 开关，单事务，仅清空非空序列号
- [x] 1.2 前置断言：目标存在且属两分公司；幂等跳过；末尾对账复核

## 2. 测试

- [x] 2.1 功能：清空后 90 台序列号为空、待补录态、他分公司/他品目零波及、对账零差异、幂等重跑
- [x] 2.2 dry-run 不写库；后端全量 pytest 通过（743 passed）

## 3. 生产执行

- [ ] 3.1 push → 部署；`/root/backup_db.sh` 即时备份
- [ ] 3.2 dry-run 存档复核（90 条逐台清单）
- [ ] 3.3 `--apply` + 内嵌对账；独立复跑 `check_ledger_consistency` exit=0
- [ ] 3.4 抽查：两司 A-a00011 序列号全空、工作手机序列号原样、他分公司零波及；幂等复证
