# nginx 配置说明

> 磐盘生产采用**三层架构**（详见 [../DEPLOYMENT.md](../DEPLOYMENT.md)），线上 nginx 配置**不在本仓库**。

```
浏览器 ──HTTPS:443──▶ root-nginx-1（公网入口，SSL 终止；配置 /root/nginx.conf）
                         │  qhpanpan.top → proxy_pass http://172.18.0.1:8080
                         ▼
                  rock-slab-nginx（磐盘 nginx，监听 8080；配置 /root/rock-slab/nginx/rock-slab.conf）
                         │  服务 frontend/dist + /api 反代 + /media + /static
                         ▼ /api/ → proxy_pass http://127.0.0.1:8002
                  rock-slab-backend（Gunicorn，8002，host 网络）
```

## 为什么仓库里没有线上 nginx 配置？

- `root-nginx-1` 是 **AI 销售教练项目的共享容器**，配置在 `/root/nginx.conf`（含 `qhpanpan.top` 与 `xsjqr.top` 两个 server 块），不属于磐盘仓库。
- `rock-slab-nginx` 容器**不在本仓库 `docker-compose.yml` 内**（手动部署），配置在服务器的 `/root/rock-slab/nginx/rock-slab.conf`。
- 历史上仓库曾有一个单层的 `qhpanpan.top.conf`（直接监听 443），在三层架构下**不会被线上加载**，已移除以免误导排障。

## 修改 nginx 配置（运维操作）

改配置后**必须先 `nginx -t` 再 reload**：

```bash
docker exec root-nginx-1  nginx -t && docker exec root-nginx-1  nginx -s reload   # 公网层
docker exec rock-slab-nginx nginx -t && docker exec rock-slab-nginx nginx -s reload # 磐盘层
```

## 上传体积限制（client_max_body_size）

资产导入模板可达数十 MB。三层链路**任一处**的 `client_max_body_size` 过小都会返回 413：

| 层 | 配置位置 | 备注 |
|----|----------|------|
| root-nginx-1 | `/root/nginx.conf` | 默认 20M，大文件导入需调到 60M |
| rock-slab-nginx | `/root/rock-slab/nginx/rock-slab.conf` | 需与上层对齐 |
| 后端 Django | `DATA_UPLOAD_MAX_MEMORY_SIZE`（见 `backend/rock_slab/settings/production.py`） | 已设 60M |

三层必须对齐，否则合法的大体积导入会在最小的那层被拦截。调大后两层 nginx 都需 reload。
