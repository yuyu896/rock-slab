## Context

`UserSerializer.create`（backend/apps/users/serializers.py:36-46）对 password 只做 `pop('password', '123456')`，显式值直入 `create_user`；update 路径 password 为 create-only（丢弃，防账号接管）；改密接口 `/api/auth/password/` 已有 validate_password。`AUTH_PASSWORD_VALIDATORS` 仅一项自定义 `MinimumLengthValidator(min_length=8)`（中文消息，apps/authentication/validators.py）。三份规范对默认口令/强度校验的要求互相矛盾，用户已裁决：123456 兜底保留、显式密码必须校验。

## Goals / Non-Goals

**Goals:**

- 显式建号密码必须通过 `AUTH_PASSWORD_VALIDATORS`，失败 400 且不落库
- 强度规则在长度之上补齐「纯数字」「与用户属性相似」两条（中文消息，与现有校验器风格一致）
- 三份规范收敛为单一并存口径，消除 E3c 文档冲突

**Non-Goals:**

- 不改 123456 兜底（产品定调；「随机初始密码+首登强制改密」留待未来提案）
- 不动 update/改密接口的密码处理结构（新校验器经 AUTH_PASSWORD_VALIDATORS 自然作用于改密）
- 不加 CommonPasswordValidator（英文常见密码表对中文场景收益低、误伤难预期，暂不引入）
- 前端零改动（建号表单本就不提交密码）

## Decisions

**1. 校验点在 `create()` 内、仅对显式密码（`'password' in validated_data`），兜底值跳过。**
兜底 123456 是产品定调的临时策略，若走校验会自相矛盾（纯数字/短）。「显式与否」以 validated_data 是否含键为准，语义精确。

**2. 相似性上下文用瞬时 `User(phone=..., name=...)`。**
`validate_password(value, user)` 的属性相似性校验需要 user；创建时实体未生，用只带 phone/name 的内存对象即可（不落库）。Django ValidationError 转 `serializers.ValidationError({'password': messages})`，错误自然挂在 password 字段（DRF 400 结构与改密接口一致）。

**3. 新校验器以 Django 内置为基类、仅覆写中文消息，放 `apps/authentication/validators.py`。**
跟随现有 `MinimumLengthValidator` 的「中文消息本地化」模式，但实现复用内置逻辑（`NumericPasswordValidator` / `UserAttributeSimilarityValidator` 子类化覆写 message），避免手写 difflib 重复造轮子。改密接口无感获得同等强度。

**4. 三份规范 MODIFIED 而非增补。**
矛盾条款（「接受弱口令」/「MUST NOT 默认密码」）是既有 requirement 的正文，ADDED 会在归档合并后留下同主题相反条款；MODIFIED 全量改写为并存口径，归档后 specs 目录只剩一套事实。

## Risks / Trade-offs

- [纯数字密码从此被拒（建号显式 + 改密两路）] → 用户可预期（错误消息中文明确）；兜底 123456 不受影响
- [与姓名相似的密码被拒，中文姓名的相似判定较宽松] → UserAttributeSimilarity 阈值 0.7，误伤概率低；错误消息可指导换密码
- [存量弱口令账号不会被追溯] → 本次只管入口；存量排查（如枚举 123456 登录态）不在范围，需要时另提运维任务

## Migration Plan

纯代码 + 配置，无迁移。部署即生效；回滚 revert。上线验证：POST /api/users/ 带 8 位纯数字密码应 400；不带密码应 201。
