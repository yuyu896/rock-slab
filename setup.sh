#!/bin/bash
set -e

echo "========== 磐盘首次部署初始化 =========="

PROJECT_DIR="/root/rock-slab"

# 1. Create project directory
echo "[1/7] 创建项目目录..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 2. Create PostgreSQL database and user
echo "[2/7] 创建 PostgreSQL 数据库..."
DB_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=' | head -c 24)
docker exec root-db-1 psql -U postgres -c "CREATE USER rock_slab_user WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "用户已存在，跳过"
docker exec root-db-1 psql -U postgres -c "CREATE DATABASE rock_slab OWNER rock_slab_user;" 2>/dev/null || echo "数据库已存在，跳过"
docker exec root-db-1 psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE rock_slab TO rock_slab_user;"

# 3. Create .env file
echo "[3/7] 创建环境配置..."
SECRET_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 50)

cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
DJANGO_SETTINGS_MODULE=rock_slab.settings.production
ALLOWED_HOSTS=qhpanpan.top,www.qhpanpan.top,47.97.43.28
DATABASE_URL=postgresql://rock_slab_user:${DB_PASSWORD}@127.0.0.1:5432/rock_slab
REDIS_URL=redis://127.0.0.1:6379/1
PORT=8002
EOF

chmod 600 .env
echo ".env 文件已创建"

# 4. Clone or upload code
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "[4/7] 请将项目代码上传到 $PROJECT_DIR"
    echo "  方式1: git clone <仓库地址> $PROJECT_DIR"
    echo "  方式2: rsync -avz --exclude node_modules ./  root@47.97.43.28:$PROJECT_DIR/"
    echo ""
    read -p "代码已就位？按回车继续..."
else
    echo "[4/7] 代码已存在，跳过"
fi

# 5. Run migrations
echo "[5/7] 执行数据库迁移..."
docker compose run --rm backend python manage.py migrate --noinput

# 6. Create superuser
echo "[6/7] 创建管理员账号..."
docker compose run --rm backend python manage.py create_superuser

# 7. Collect static files
echo "[7/7] 收集静态文件..."
docker compose run --rm backend python manage.py collectstatic --noinput

echo ""
echo "========== 初始化完成 =========="
echo ""
echo "接下来请执行:"
echo "  1. 构建前端: cd $PROJECT_DIR/frontend && npm install && npm run build"
echo "  2. 启动后端: cd $PROJECT_DIR && docker compose up -d"
echo "  3. 签发 SSL: bash $PROJECT_DIR/setup-ssl.sh"
echo "  4. 部署 Nginx 配置: bash $PROJECT_DIR/setup-nginx.sh"
