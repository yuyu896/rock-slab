## 1. 纠错命令实现

- [x] 1.1 新建 `backend/apps/assets/management/commands/prod_data_fix_hz5.py`：常量固化（5分杭州），复用 hz2 合体路径（实例侧出生单连删 + 建账侧成对删 + 全零残行清理）
- [x] 1.2 前置断言：出生单纯实例行且生效、镜像三列、非实例品目无流转单据行与错挂实例；幂等跳过；末尾内嵌对账复验

## 2. 测试

- [x] 2.1 功能+边界+安全（同 hz2 测试面：合体清零/镜像拒绝/错挂拒绝/dry-run/幂等）
- [x] 2.2 后端全量 pytest 通过（718 passed）

## 3. 生产执行（不推送通道）

- [ ] 3.1 本地 commit（**不 push**）；命令文件 scp 至服务器 /root/
- [ ] 3.2 `docker compose run --rm -v ...prod_data_fix_hz5.py:...` 挂载 dry-run 复核（1 单 127 实例 −67/−60；45 调整单 + 44 行）
- [ ] 3.3 `/root/backup_db.sh` 备份 → 挂载 `--apply` + 内嵌对账；独立复跑 `check_ledger_consistency` exit=0
- [ ] 3.4 抽查：实例/台账/调整单全归零、员工饶智依在；幂等复证
