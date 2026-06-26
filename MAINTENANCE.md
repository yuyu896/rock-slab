# 磐盘后期维护手册

磐盘（Rock Slab）生产环境上线后的日常运维、监控、排障、更新流程。配套 [DEPLOYMENT.md](DEPLOYMENT.md)（部署细节）使用。

> 服务器：阿里云 ECS 47.97.43.28 · 域名 https://qhpanpan.top · 项目目录 `/root/rock-slab`

---

## 一、例行巡检（建议频率）

### 每天（可选，低优先）
```bash
# 健康检查
curl -s https://qhpanpan.top/api/health/        # 期望 {"status": "ok"}
```

### 每周
```bash
# 1. 备份是否在自动生成（看最新文件日期）
ls -lht /root/backups/ | head -3
cat /root/backups/backup.log | tail -5

# 2. 容器是否健康
docker ps --format "table {{.Names}}\t{{.Status}}" | grep rock-slab

# 3. SSL 证书到期时间（提前续期由 certbot 自动处理，此为确认）
certbot certificates | grep -A1 qhpanpan.top

# 4. 磁盘空间（备份和日志会占用）
df -h / | tail -1
du -sh /root/backups/ /var/lib/docker/ 2>/dev/null
```

### 每月
```bash
# 清理无用 Docker 镜像/层（释放磁盘，注意别影响在用容器）
docker image prune -f
docker builder prune -f

# 检查系统更新
dnf check-update
```

---

## 二、监控要点

| 指标 | 命令 | 告警阈值 |
|------|------|----------|
| 后端健康 | `curl -s -o /dev/null -w "%{http_code}" https://qhpanpan.top/api/health/` | 非 200 |
| 容器状态 | `docker ps` 看 rock-slab-backend / rock-slab-nginx | 非 Up |
| 磁盘 | `df -h /` | 使用率 > 85% |
| 内存 | `free -h` | 可用 < 500MB |
| 后端错误 | `docker logs --since 1h rock-slab-backend 2>&1 \| grep -i error` | 出现 500/Traceback |
| 数据库连接 | `docker exec root-db-1 pg_isready -U rock_slab_user` | 非 accepting |

---

## 三、更新部署流程

### 3.1 后端有改动时
```bash
cd /root/rock-slab
git pull origin main
docker compose build backend          # pip 走阿里云镜像，通常 1 分钟内
docker compose up -d backend          # entrypoint 自动 migrate + collectstatic
sleep 10
docker logs --tail 20 rock-slab-backend    # 确认无报错
curl -s https://qhpanpan.top/api/health/   # 确认 200
```

### 3.2 前端有改动时
```bash
cd /root/rock-slab/frontend
git pull origin main        # 若前端改动已含在后端的 pull 里可跳过
npm install                 # 依赖有变才需要
npm run build               # 生成新 dist，rock-slab-nginx 直接服务，无需重启
```

### 3.3 公网 nginx 配置改动后
```bash
docker exec root-nginx-1 nginx -t            # 先测语法（必做，失败别 reload）
docker exec root-nginx-1 nginx -s reload     # 语法 OK 才重载
```

> ⚠️ 改 `/root/nginx.conf` 后**必须先 `nginx -t`** 再 reload。语法错误会导致 reload 失败，但旧 worker 仍在运行；若已 stop 则全站宕机。

### 3.4 上传体积限制（导入大文件 413 排障）

资产导入模板可达数十 MB。三层链路任一处的 `client_max_body_size` 过小都会被拦成 413：

- `root-nginx-1`：`/root/nginx.conf`（线上当前 20M，大文件导入需调到 60M）
- `rock-slab-nginx`：`/root/rock-slab/nginx/rock-slab.conf`（需与上层对齐）
- 后端 Django：`DATA_UPLOAD_MAX_MEMORY_SIZE`（`backend/rock_slab/settings/production.py` 已设 60M）

调大后两层 nginx 都需 reload（见 3.3）。详见 [nginx/README.md](nginx/README.md)。

---

## 四、备份与恢复

### 4.1 手动备份
```bash
/root/backup_db.sh                              # 立即备份
ls -lht /root/backups/rock_slab_*.sql.gz | head # 查看备份
```

### 4.2 自动备份（已配）
- 时间：每日 03:07
- 保留：最近 14 天（旧备份自动删除）
- 日志：`/root/backups/backup.log`
- cron 查询：`crontab -l | grep backup`

### 4.3 恢复数据库（慎用，会覆盖现有数据）
```bash
# 1. 先停后端，避免恢复期间写入
docker compose stop backend

# 2. 从备份恢复
gunzip < /root/backups/rock_slab_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i root-db-1 psql -U rock_slab_user -d rock_slab

# 3. 重启后端
docker compose up -d backend
```

### 4.4 下载备份到本地（异地保存，强烈建议）
```bash
# 在本地机器执行
scp root@47.97.43.28:/root/backups/rock_slab_最新.sql.gz ./
```

---

## 五、常见故障排查

### 5.1 网站打不开
```bash
# 按链路逐层排查：浏览器 → root-nginx-1 → rock-slab-nginx → backend
docker ps | grep -E "rock-slab|root-nginx"      # 容器都在吗
curl -s http://localhost:8002/api/health/        # 后端通吗（应为 ok）
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: qhpanpan.top" https://localhost/  # nginx 通吗
curl -s https://qhpanpan.top/api/health/         # 公网通吗
```

### 5.2 登录失败（401/500）
- **401 账号密码错误**：确认账号存在且密码正确
  ```bash
  docker compose exec backend python manage.py shell -c "
  from apps.users.models import User
  u=User.objects.get(phone='13800000001')
  print('密码123456:', u.check_password('123456'), '| 状态:', u.status)"
  ```
- **500 登录报错**：可能是孤儿 token（多表继承残留），清理：
  ```bash
  docker compose exec backend python manage.py shell -c "
  from rest_framework.authtoken.models import Token as B
  from apps.authentication.models import ExpiringToken as E
  n=B.objects.exclude(user_id__in=E.objects.values_list('user_id',flat=True)).count()
  B.objects.exclude(user_id__in=E.objects.values_list('user_id',flat=True)).delete()
  print('清理孤儿 token:', n)"
  ```
- **重置某用户密码**：
  ```bash
  docker compose exec backend python manage.py shell -c "
  from apps.users.models import User
  u=User.objects.get(phone='13800000001')
  u.set_password('新强密码'); u.save(); print('密码已重置')"
  ```

### 5.3 后端 500（通用）
```bash
docker logs --tail 80 rock-slab-backend 2>&1 | grep -A30 Traceback
```
看 Traceback 定位。常见：迁移未应用（`docker compose exec backend python manage.py migrate`）、Redis/DB 连接断。

### 5.4 SSL 证书问题
```bash
certbot certificates                    # 查到期与状态
# 紧急手动续期（certbot 会停启 root-nginx-1）
certbot renew --cert-name qhpanpan.top --force-renewal
```

### 5.5 容器反复重启
```bash
docker logs rock-slab-backend 2>&1 | tail -40   # 看启动失败原因
docker compose exec backend python manage.py check   # Django 自检
```

### 5.6 静态文件（CSS/JS/图片）404
```bash
# collectstatic 没跑或 staticfiles 目录空
docker compose exec backend python manage.py collectstatic --noinput
ls /root/rock-slab/backend/staticfiles/         # 确认有内容
```

---

## 六、安全维护

| 任务 | 命令/说明 | 频率 |
|------|----------|------|
| 改强密码 | 管理员账号（当前 123456）用 set_password 改强密码 | 立即 + 定期 |
| 看登录爆破 | `lastb \| head` / `journalctl -u sshd \| grep Failed` | 定期 |
| 关不必要端口 | `firewall-cmd --list-all`，确认只 22/80/443；5432/6379/8080 不对公网 | 定期 |
| 升级依赖 | 后端 `pip` 安全补丁、Docker 基础镜像 | 季度 |
| 检查 .env 权限 | `ls -l /root/rock-slab/.env` 应仅 root 可读 | 定期 |

> ⚠️ 数据库 5432、Redis 6379 由 Docker 发布在 0.0.0.0，可能绕过 firewalld。如需彻底关闭外部访问，应改 docker-compose（root-* 项目）的端口绑定为 127.0.0.1，或用 Docker 网络隔离。

---

## 七、应急联系与回滚

### 7.1 部署回滚（双轨，按问题类型选择）

`deploy.sh` 会在每次部署开头输出两个锚点：
- `部署前 commit`：`PRE_DEPLOY_COMMIT`（部署前的 git SHA）
- `部署前备份`：`PRE_DEPLOY_BACKUP`（部署前即时 `pg_dump` 文件路径）

> 本次权限解耦部署的 permissions 表/字段是**新增**，旧代码不引用它们——回滚代码后这些表保留在库里**无害**。

**① 代码回滚**（前端样式 / 页面 / 逻辑 bug，**数据库正常**）——秒级，不动数据：
```bash
cd /root/rock-slab
git reset --hard <PRE_DEPLOY_COMMIT>
docker compose build backend
cd frontend && npm install && npm run build && cd ..
docker compose up -d backend
docker exec root-nginx-1 nginx -s reload
```

**② 数据回滚**（迁移 / 种子异常，或需恢复部署前数据）——分钟级：
```bash
cd /root/rock-slab
docker compose stop backend                                   # 1. 停后端，避免恢复期间写入
gunzip -c <PRE_DEPLOY_BACKUP> | docker exec -i root-db-1 psql -U rock_slab_user -d rock_slab  # 2. 恢复
git reset --hard <PRE_DEPLOY_COMMIT>                          # 3. 代码也回滚
docker compose up -d backend                                  # 4. 重启
docker exec root-nginx-1 nginx -s reload
```

> 上面 `<PRE_DEPLOY_COMMIT>` / `<PRE_DEPLOY_BACKUP>` 替换为 `deploy.sh` 末尾打印的实际值。
> 种子校验失败时，`deploy.sh` 第 5 步会自动 `exit 1` 中止——此时 migrate 已跑、后端**未重启**，直接走②数据回滚即可。

### 7.2 其他应急

- **代码回滚（历史）**：`cd /root/rock-slab && git log --oneline -10` 找上一个稳定 commit → `git reset --hard <hash>` → rebuild
- **数据回滚（历史）**：见四、4.3，从备份恢复
- **全站宕机急救**：`cd /root/rock-slab && docker compose up -d backend` + `docker exec root-nginx-1 nginx -s reload`


---

## 八、相关文档
- [DEPLOYMENT.md](DEPLOYMENT.md) — 初始部署细节、架构图、凭据位置
- [CLAUDE.md](CLAUDE.md) — 项目技术栈与架构约定
- 代码仓库：https://github.com/yuyu896/rock-slab
