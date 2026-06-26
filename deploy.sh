#!/bin/bash
set -e

PROJECT_DIR="/root/rock-slab"
cd "$PROJECT_DIR"

echo "========== 磐盘部署开始 =========="

# 0. 记录部署前锚点（commit SHA）+ 磁盘检查
PRE_DEPLOY_COMMIT=$(git rev-parse HEAD)
echo "[0/9] 部署前 commit: $PRE_DEPLOY_COMMIT"
echo "      磁盘空间:" && df -h / | tail -1

# 1. 部署前即时数据库备份（区别于每日 03:07 自动备份，确保有"部署前那一刻"快照）
echo "[1/9] 部署前即时数据库备份..."
/root/backup_db.sh
PRE_DEPLOY_BACKUP=$(ls -t /root/backups/rock_slab_*.sql.gz | head -1)
echo "      备份文件: $PRE_DEPLOY_BACKUP"

# 2. Pull latest code
echo "[2/9] 拉取最新代码..."
git pull origin main

# 3. Install backend dependencies
echo "[3/9] 安装后端依赖..."
docker compose build --no-cache backend

# 4. Run database migrations
echo "[4/9] 执行数据库迁移..."
docker compose run --rm backend python manage.py migrate --noinput

# 5. 验证种子授权（迁移后、重启前；异常 exit 1 中止部署）
echo "[5/9] 校验种子授权结果..."
docker compose run --rm backend python manage.py check_seed_grants

# 6. Collect static files
echo "[6/9] 收集静态文件..."
docker compose run --rm backend python manage.py collectstatic --noinput

# 7. Build frontend
echo "[7/9] 构建前端..."
cd frontend
npm install
npm run build
cd ..

# 8. Restart backend container
echo "[8/9] 重启后端容器..."
docker compose up -d backend

# 9. Reload Nginx
echo "[9/9] 重载 Nginx 配置..."
docker exec root-nginx-1 nginx -s reload

# 10. Health check
echo "==== 健康检查 ===="
sleep 5
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/api/health/)
if [ "$HEALTH" = "200" ]; then
    echo ""
    echo "========== 部署成功 =========="
    echo "访问地址: https://qhpanpan.top"
    echo "健康检查: OK"
else
    echo ""
    echo "========== 部署完成（健康检查异常）=========="
    echo "健康检查返回状态码: $HEALTH"
    echo "请检查后端日志: docker compose logs backend"
fi

echo ""
echo "========== 回滚锚点（如需回滚请参考）=========="
echo "部署前 commit : $PRE_DEPLOY_COMMIT"
echo "部署前备份    : $PRE_DEPLOY_BACKUP"
echo "代码回滚: git reset --hard $PRE_DEPLOY_COMMIT && docker compose build backend && (cd frontend && npm run build && cd ..) && docker compose up -d backend && docker exec root-nginx-1 nginx -s reload"
echo "数据回滚: docker compose stop backend && gunzip -c $PRE_DEPLOY_BACKUP | docker exec -i root-db-1 psql -U rock_slab_user -d rock_slab && git reset --hard $PRE_DEPLOY_COMMIT && docker compose up -d backend"
