#!/bin/bash
set -e

PROJECT_DIR="/root/rock-slab"
cd "$PROJECT_DIR"

echo "========== 磐盘部署开始 =========="

# 1. Pull latest code
echo "[1/8] 拉取最新代码..."
git pull origin main

# 2. Install backend dependencies
echo "[2/8] 安装后端依赖..."
docker compose build --no-cache backend

# 3. Run database migrations
echo "[3/8] 执行数据库迁移..."
docker compose run --rm backend python manage.py migrate --noinput

# 4. Collect static files
echo "[4/8] 收集静态文件..."
docker compose run --rm backend python manage.py collectstatic --noinput

# 5. Build frontend
echo "[5/8] 构建前端..."
cd frontend
npm install
npm run build
cd ..

# 6. Restart backend container
echo "[6/8] 重启后端容器..."
docker compose up -d backend

# 7. Reload Nginx
echo "[7/8] 重载 Nginx 配置..."
docker exec root-nginx-1 nginx -s reload

# 8. Health check
echo "[8/8] 健康检查..."
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
