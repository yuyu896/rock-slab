#!/bin/bash
# 对账模块专项发布入口（兼容旧命令）。
# 对账数据已稳定；此脚本只调用常规部署流程，绝不清理对账数据。
# 使用：bash scripts/deploy_reconciliation_v2.sh
# 在本机执行，通过 SSH 操作服务器。

set -e

SERVER="root@47.97.43.28"
PROJECT_DIR="/root/rock-slab"

echo "=========================================="
echo "  对账模块常规部署"
echo "  保留现有全部对账数据"
echo "=========================================="
echo ""
echo "即将通过 SSH 执行常规 deploy.sh。不会清理对账任务、问题或比较记录。"
echo "继续？[y/N]"
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "已取消；未连接服务器，也未更改任何数据。"
    exit 0
fi

echo "执行常规部署..."
ssh "$SERVER" "cd $PROJECT_DIR && bash deploy.sh"
