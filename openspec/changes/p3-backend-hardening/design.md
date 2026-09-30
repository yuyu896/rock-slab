## Context

User 经裸 ModelAdmin 注册（apps/users/admin.py），表单含 password 列（AbstractBaseUser 可编辑直写）、status 停用不联动 is_active/token 清理——API 序列化器做的三件事（权线闸、is_active 联动、token 清理）admin 路径全绕过。生产 `/admin/` 仅 SSH 隧道可达、超管从未登录，但纵深防御要求关闭旁路。`wsgi.py` setdefault development：部署链路（compose environment）显式注入 production，风险仅在绕过 compose 直跑 gunicorn 的兜底场景。

## Goals / Non-Goals

**Goals:**

- User 的写入口唯一化：只有 API（带全部闸门）
- WSGI 入口缺省 fail-safe 到生产配置

**Non-Goals:**

- 不移除 admin 站点本身（其他模型只读排障有用；如需彻底下线另议）
- 不动 manage.py 缺省（开发工具，改了破坏本地 DX——所有本地 shell/migrate/命令都依赖它）
- 不给 admin 做 User 加固版（重写 save_model/表单是给旁路修路，不如拆路）

## Decisions

**1. 反注册优于加固。**
给 admin 写一个「正确的」UserAdmin（save_model 联动、排除 password、token 清理）= 在旁路上复刻 API 行为，两处实现永久漂移风险；反注册一行终结。运维修数据走 `manage.py shell`（可审计的会话记录），与既有 MAINTENANCE.md 的运维口径一致。

**2. wsgi 缺省 production、manage 缺省 development，注释写明分工。**
WSGI 是部署入口——漏配环境变量时宁可 fail-safe 到严格配置（PROD 配置连不上库会启动失败并暴露问题，好过 development 静默跑在宽松配置上）。manage.py 是人手开发工具，缺省 development 是 DX 刻意选择。

## Risks / Trade-offs

- [有人依赖 admin 改用户的工作习惯被打破] → 生产超管从未登录（last_login=None），无存量习惯；shell 方式已有文档惯例
- [wsgi 缺省 production 后，本地直接跑 gunicorn/wsgi 需显式设 development] → 本地开发用 runserver（manage.py 路径），不触 wsgi；受影响面近零

## Migration Plan

纯代码，无迁移。部署即生效；回滚 revert。上线验证：`/admin/` 用户列表不再出现 User 模型；容器未设环境变量的 hypothetical 直跑 wsgi 场景加载 production 配置。
