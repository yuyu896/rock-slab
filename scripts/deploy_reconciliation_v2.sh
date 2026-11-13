#!/bin/bash
# 对账模块 V2 专项部署脚本
# 用途：清空生产对账测试数据 → 部署新版本
# 使用：bash scripts/deploy_reconciliation_v2.sh
# 在本机执行，通过 SSH 操作服务器

set -e

SERVER="root@47.97.43.28"
PROJECT_DIR="/root/rock-slab"
BACKEND_CONTAINER="rock-slab-backend"

echo "=========================================="
echo "  对账 V2 专项部署"
echo "=========================================="
echo ""

# ── Step 1：备份数据库 ──────────────────────────────
echo "[1/4] 备份生产数据库..."
BACKUP_FILE=$(ssh "$SERVER" "/root/backup_db.sh 2>&1 | tail -1")
echo "      $BACKUP_FILE"
echo ""

# ── Step 2：清空对账测试数据 ───────────────────────
echo "[2/4] 清空对账模块测试数据..."
ssh "$SERVER" "docker exec $BACKEND_CONTAINER python manage.py shell -c \"
from apps.reconciliation.models import ReconciliationTask, ReconciliationIssue, ReconciliationComparison
print('  清理前：Tasks=%d  Issues=%d  Comparisons=%d' % (
    ReconciliationTask.objects.count(),
    ReconciliationIssue.objects.count(),
    ReconciliationComparison.objects.count(),
))
ReconciliationIssue.objects.all().delete()
ReconciliationComparison.objects.all().delete()
ReconciliationTask.objects.all().delete()
print('  清理后：Tasks=%d  Issues=%d  Comparisons=%d' % (
    ReconciliationTask.objects.count(),
    ReconciliationIssue.objects.count(),
    ReconciliationComparison.objects.count(),
))
print('  对账数据清理完成')
\""
echo ""

# ── Step 3：确认继续 ───────────────────────────────
echo "[3/4] 即将执行 deploy.sh，继续？[y/N]"
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "已取消。对账数据已清理，可单独手动运行 deploy.sh。"
    exit 0
fi
echo ""

# ── Step 4：执行部署 ───────────────────────────────
echo "[4/4] 执行 deploy.sh..."
ssh "$SERVER" "cd $PROJECT_DIR && bash deploy.sh"
