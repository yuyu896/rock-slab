#!/bin/sh
set -e

# 传入命令时直接执行（供 docker compose run 跑一次性任务：migrate / check_seed_grants / collectstatic）
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

echo "========== 磐盘后端启动 =========="

echo "[1/3] 应用数据库迁移..."
python manage.py migrate --noinput

echo "[2/3] 收集静态文件..."
python manage.py collectstatic --noinput

echo "[3/3] 启动 Gunicorn..."
exec gunicorn rock_slab.wsgi:application -c gunicorn.conf.py
