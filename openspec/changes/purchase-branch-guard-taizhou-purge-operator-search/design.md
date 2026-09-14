# 采购守卫+台州清数+搜经办人 — 技术设计

## Context

生产事实：624 张采购单 to_branch 空但 from_branch 全有值（员工分公司列填了、导入代码装反到调出字段）；台州 199 实例/4 台账/1 生效采购单为误录；keyword 过滤不含经办人。

## Goals / Non-Goals

**Goals:** 导入分公司行级守卫；生产删 625 张垃圾单；台州定向清数；keyword 匹配经办人。

**Non-Goals:** 不动导入模板结构；不动其他分公司数据；回收台账 keyword 不动。

## Decisions

### D1：导入方向修复

import 建单 purchase 分支 header 的 `'调出分公司': branch_name` 改 `'调入分公司': branch_name`（_resolve_branches 解析 to_branch 并回填文本）；行级守卫 label 改「入库分公司」（空值拒绝本就在位）。

### D2：生产运维脚本式执行（先备份）

624 张对调回填：from_branch 值搬到 to_branch、调出分公司文本搬到调入分公司、from 置空（采购无调出方）——员工填的分公司本就正确，纯字段对调，无映射歧义。对调后待审批单审批生效即走正确入库分公司。台州：删 1 张生效采购单（行/实例关联级联）→ 199 实例（branch=tz）→ 4 台账行 → 台州序列行 → 对账验证。均单事务；备份先行。

### D3：keyword 加两列 OR

`filters.py` filter_keyword 追加 `Q(采购经办人__icontains=value) | Q(创建人__icontains=value)`；四个流转列表 + placeholder 文案统一改「搜索单号、品目、经办人...」。

## Risks / Trade-offs

- [删单的级联面] — 通知/审计有 FK 级联属预期（垃圾单连带清理）；对账守卫验证兜底
- [keyword 宽匹配误中] — 经办人姓名与品目重名概率低，可接受

## Migration Plan

代码随部署；生产清理在部署后执行（脚本已含对账验证）。

## Open Questions

（无）
