# 任务：移动端扫码终端生产发布（2026-09-17）

- [x] 1. 生产 PostgreSQL 全量备份（root-db-1 → /root/rock_slab_full_backup_20260917_*.sql），确认文件非空
- [x] 2. 服务器 git pull（HTTP/1.1 重试；连败走本地 bundle 直推兜底），确认拉到 d321e27
- [x] 3. 执行 bash deploy.sh（对账门禁 exit=0）
- [x] 4. 线上验收：/install 公开可达与四分支、/mobile/scan 扫码终端三项导航、工作台二维码解码=生产地址、打印标签 V3 五行前缀
- [x] 5. 数据隔离核验：生产无 BJ001-3..22 测试实例与测试盘点任务，既有数据原样
