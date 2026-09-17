# 设计：移动端扫码终端发布部署

## Context

生产为三层容器架构（root-nginx-1 → rock-slab-nginx → rock-slab-backend），`bash deploy.sh` 一键完成 git pull → migrate（本次 no-op）→ 对账门禁 → collectstatic → 前端构建 → nginx reload。本轮待部署提交全部为前端（标签系列、扫码终端、PWA、安装向导）。服务器拉 GitHub 常超时（HTTP/2 问题），需 HTTP/1.1 + 重试，仍失败则本地 bundle 直推兜底。

## 部署序列（带备份与回滚点）

1. **备份**：`docker exec root-db-1 pg_dump` 全量到 `/root/rock_slab_full_backup_20260917_*.sql`——虽无数据变更，仍按铁律留回滚点
2. **拉码**：服务器 `git pull`（HTTP/1.1，失败重试 3 次；连败则本地 `git bundle` scp 直推）
3. **执行** `bash deploy.sh`：对账门禁（check_ledger_consistency）必须 exit=0
4. **验收**：
   - 线上 `/install` 200 且四分支文案正确（未登录可达）
   - `/mobile/scan` 登录后扫码终端加载（三项导航）
   - 工作台安装卡片二维码解码 = `https://qhpanpan.top/install`
   - 生产实例列表无 `A-a00008-BJ001-3..22` 测试数据（数据隔离核验）
   - 打印标签弹窗 V3 五行前缀正常
5. **回滚预案**：任一步失败 → 停止发布；已发布出问题 → git reset 到部署前 commit + 重跑 deploy.sh；数据异常 → pg 备份恢复

## 数据隔离声明

deploy.sh 无任何数据通道（仅代码/构建/静态资源）。本地 SQLite 的测试数据物理上不可能进入生产 PostgreSQL。对账门禁在生产跑的是生产自身数据的一致性。
