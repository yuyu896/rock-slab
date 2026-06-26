## 1. 增强 deploy.sh（备份 + 验证 + 锚点）

- [x] 1.1 在 `deploy.sh` 的 `git pull` **之前**插入：记录 `PRE_DEPLOY_COMMIT=$(git rev-parse HEAD)` 与磁盘检查 `df -h /`
- [x] 1.2 调用 `/root/backup_db.sh` 即时备份；捕获 `PRE_DEPLOY_BACKUP=$(ls -t /root/backups/*.sql.gz | head -1)`；echo 出 commit 与备份路径
- [x] 1.3 在 `migrate` 之后、`up -d backend` 之前，插入 `python manage.py check_seed_grants`；异常 `exit 1` 中止（`set -e` 生效）
- [x] 1.4 部署末尾 echo 回滚锚点与两条回滚命令（commit SHA + 备份路径）

## 2. 验证脚本/命令（迁移后种子校验）

- [x] 2.1 新增 `apps/permissions/management/commands/check_seed_grants.py`：打印 scope/grant 计数、各 role 抽样、无 region/branch 用户清单
- [x] 2.2 校验通过条件：counts 合理且抽样用户授权与旧 role 隐含一致；异常 `raise SystemExit(1)`（开发库已验证：20 scopes / 51 grants，抽样通过）

## 3. 回滚预案文档化

- [x] 3.1 `MAINTENANCE.md` 七、增"部署回滚（双轨）"：代码回滚（git reset + rebuild + 重启，不动 DB）与数据回滚（stop backend → psql 恢复 PRE_DEPLOY_BACKUP → 重启）
- [x] 3.2 明确回滚后 permissions 表/字段保留无害（旧代码不引用）

## 4. 执行部署（服务器，由用户执行）

- [ ] 4.1 本地确认所有改动 commit + `git push origin main`，记录待部署 SHA
- [ ] 4.2 SSH 服务器，低峰窗口执行增强后的 `deploy.sh`
- [ ] 4.3 部署后冒烟：`/api/health/` 200；登录；资产列表 / 品目（只读 vs 写入口）/ 盘点创建 / 权限分配页面各验证
- [ ] 4.4 核对 check_seed_grants 输出中无 region/branch 用户，在权限分配页面补授

## 5. 部署后收尾（由用户观察）

- [ ] 5.1 确认每日自动备份恢复正常（`ls -lht /root/backups/`）
- [ ] 5.2 观察后端日志 24h 无异常（`docker compose logs backend`）
- [ ] 5.3 归档本次部署记录（commit SHA、备份文件名、无授权用户处理结果）
