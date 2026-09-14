# 单据分公司语义化 — 技术设计

## Context

现状赋值点仅 2 处（views._create_action、import_excel）；读取方（ledger._line_plan/instances/序列化）已按类型分支。第 24 案教训：约定靠人记 → 装反。

## Goals / Non-Goals

**Goals:** 语义化构造器唯一写入口 + 业务分公司属性 + 架构测试禁直赋。

**Non-Goals:** 列改名/API 变更/读取方强制迁移。

## Decisions

### D1：build 类方法承载映射，中文名参数对齐业务语言

`Transfer.build(action_type, *, 所属分公司=None, 调出分公司=None, 调入分公司=None, **fields)`：purchase→(None, 所属分公司)；transfer→(调出分公司, 调入分公司)；assign/return/recovery→(所属分公司, None)；非白名单参数传入（如采购传了所属分公司以外的方向参数）抛 ValidationError——参数即业务校验。`**fields` 透传其余单头字段（保持现有 _create_action 的 data dict 兼容）。

### D2：业务分公司属性

`@property def 业务分公司`：采购→to_branch 其余→from_branch。文本版 `业务分公司名` 同理（调入/调出文本）。读取方（如 scope/对账未来）可渐进迁移。

### D3：调用点改造

`_create_action`：解析出 from/to 后改传语义参数（transfer 双参、其余类型传所属分公司）。import_excel：采购分支 header 已是「调入分公司」文本（24 案修复后），Transfer 构造改 build(action_type, 所属分公司=branch_cache[...])；其他类型同构。

### D4：架构测试

复用实例写守卫模式：扫描 apps/**/*.py（排除 migrations/tests/models.py），正则抓 `from_branch\s*=` / `to_branch\s*=`（含构造关键字参数）——models.py 白名单承载唯一映射。

## Risks / Trade-offs

- [中文参数名] — 项目模型字段本就中文（分公司/单据编号），风格一致；IDE 支持无碍
- [build 透传 **fields 弱类型] — 与既有 _create_action data dict 等宽，不新增风险

## Migration Plan

纯代码收口，无迁移；deploy 全绿即可（对账不涉）。

## Open Questions

（无）
