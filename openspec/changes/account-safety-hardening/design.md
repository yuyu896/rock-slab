## Context

头像双 action 同 url_path 的 405 是已知 DRF 路由坑（assets/views.py 的 image action 注释即引用本例为先例并已用合并分流解法）。UserSerializer.phone 显式声明 `validators=[phone_validator]` 覆盖 ModelSerializer 自动生成的 UniqueValidator。account_lockout 用 locmem/Redis cache。audit 装饰器的 finally 段创建日志，result 为 DRF Response 时可读 status_code。health_check 是裸 Django 视图，deploy.sh 与容器健康检查依赖其 200/503 状态。

## Goals / Non-Goals

**Goals:** POST /avatar 可用；撞号 400；计数原子；审计 is_success 与 HTTP 语义一致；health 不泄露内部信息。

**Non-Goals:** 不给 health 加鉴权（会破坏容器/deploy 探活）；不开 SECURE_SSL_REDIRECT（外层 nginx 统一终止 SSL 的既有架构决策，backend 层开启有重定向循环风险）；不改头像上传校验逻辑本身。

## Decisions

**1. 头像合并 action 照抄 assets/image 先例：`methods=['post','delete']` 单 action，内按 `request.method` 分流，共用既有权限注释与校验。**
两个旧 action 的 permission_classes 均为 `[IsAuthenticated]` 且内部做本人/admin 校验，合并无权限面变化。

**2. phone 的 UniqueValidator 显式声明（带中文 message），格式校验保留。**
ModelSerializer 的自动 UniqueValidator 在 update 场景默认含实例排除（UniqueValidator(queryset) 在序列化器有 instance 时自动 exclude self）——显式声明同样享受该行为，改自己手机号不变为撞号。

**3. 计数 `cache.incr` + ValueError 初始化。**
Django cache 后端的 incr 契约：键不存在抛 ValueError。首败 set(1, WINDOW)，后续 incr（Redis INCR 不动 TTL）→ 固定窗。锁定判定/清零逻辑不变。

**4. is_success 全局修：`isinstance(result, Response) and result.status_code >= 400 → False`，error_msg 取 detail 摘要。**
一处修正惠及所有挂装饰器视图（改密 400、各类 400 校验失败）。现有测试若锚定「400 记成功」需同步（属修正目标）。

**5. health 异常分支：`{'status': 'error'}`，`logger.exception` 留服务端痕迹。**

## Risks / Trade-offs

- [固定窗计数：首败后第 5 分钟起旧失败不再计入] — 阈值 10 次/5 分钟的防护强度基本不变；原子性收益优先
- [is_success 全局修正影响存量断言] — 全量 pytest 兜底，逐个修正锚定旧行为的用例

## Migration Plan

纯代码。部署即生效。验证：POST /api/users/{id}/avatar 上传成功；重复手机号建号 400；改密旧错 400 后审计 is_success=false；curl /api/health/ 故障时不泄露连接串。
