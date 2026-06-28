## 1. 本地准备：提交 + 推送

- [x] 1.0 修复前端密码长度不一致：`PasswordChangeModal` 占位符"至少6位"→"至少8位"、前端校验 `< 6`→`< 8`（与后端 `min_length=8` 对齐）
- [x] 1.0b UX：账号锁定提示加时长——`account_lockout.check_account_locked` 改为"请 {LOCKOUT_DURATION//60} 分钟后再试"
- [ ] 1.1 提交 4 个未提交的报表文件 + 上述前端一致性修复
- [ ] 1.2 `git push origin main`（推送 7+1 个提交）
- [ ] 1.3 记录待部署 SHA（应为 `86291d1` 或之后）

## 2. 服务器部署（复用增强版 deploy.sh）

- [ ] 2.1 SSH `47.97.43.28`，`cd /root/rock-slab`，确认工作区干净（上次清理后应仅 `.env.bak*` 未跟踪）
- [ ] 2.2 `df -h /` 确认磁盘
- [ ] 2.3 低峰窗口执行 `bash deploy.sh`（备份→pull→build→migrate[no-op]→check_seed_grants→collectstatic→npm build→重启→nginx reload→健康检查）
- [ ] 2.4 确认健康检查 200；记录末尾打印的 `PRE_DEPLOY_COMMIT` 与备份路径

## 3. 功能冒烟（本次新功能重点）

- [ ] 3.1 登录限流与账号锁定（两套独立机制）：同一 IP 连续登录 >5 次/分钟触发限流（429，提示可见）；同一手机号 10 次失败/5 分钟触发账号锁定 15 分钟（403，提示"账号已被临时锁定，请 15 分钟后再试"可见）；两者错误提示均能正常显示（不吞错）
- [ ] 3.2 密码强度：改密码窗口占位符显示"至少8位"；输 6-7 位被前端拦截提示"不少于8位"；≥8 位正常修改；既有短密码仍能登录
- [ ] 3.3 资产/固定资产导入：模板下载、按列名映射导入、大文件（接近 60MB）可上传
- [ ] 3.4 报表数据隔离：非 admin 按授权范围看到报表数据（不越权）
- [ ] 3.5 审批并发：重复点击审批不产生重复生效（幂等）；并发入库不超卖（行锁）
- [ ] 3.6 上传校验：非法文件类型/超大文件被拒并提示
- [ ] 3.7 回归抽样：登录、资产列表、品目、盘点、权限分配仍正常（上次已全量验过，本次抽样）

## 4. 配置核对与告知

- [ ] 4.1 核对 nginx `client_max_body_size` ≥ 60MB（`docker exec root-nginx-1 nginx -T | grep client_max_body_size`），不足则调整并 reload
- [ ] 4.2 核对 `NUM_PROXIES`：限流是否按真实客户端 IP 计数（若误按容器 IP，设 `.env` 的 `NUM_PROXIES`）
- [ ] 4.3 告知用户预期行为变化（弱密码被拒、登录失败锁定、大文件可上传）

## 5. 收尾

- [ ] 5.1 观察后端日志 24h（`docker compose logs backend`）无异常
- [ ] 5.2 确认每日自动备份正常（`ls -lht /root/backups/`）
- [ ] 5.3 异常则用 `deploy.sh` 末尾的代码回滚命令（`git reset --hard $PRE_DEPLOY_COMMIT` + rebuild + 重启，无需数据恢复）
