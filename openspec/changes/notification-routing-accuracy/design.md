## Context

signals.py 路由现状：`notify_transfer_created` 与审批通过抄送都用 `instance.调出分公司` 文本；`_users_with_operation_access` 对 branch=None 返回全量候选（注释自称「避免漏发」实为广播）；pre_save 只认 `待审批→已通过`；创建人 `User.objects.filter(name=instance.创建人).first()`。`Transfer.业务分公司` property（models.py）已编码正确分公司口径。position-appointment-permissions 规范要求「接收人=持 approve_transfer（或 admin）且数据范围覆盖相关分公司的活跃用户，MUST NOT 按角色列表筛人」——现状代码违反该规范，本变更使其合规。

## Goals / Non-Goals

**Goals:**

- 待审批/抄送通知到达且仅到达「范围覆盖业务分公司」的应接收人
- 采购（已入库）与普通单据（已通过）的审批结果通知行为一致
- 创建人定位精确到人（外键），存量无 FK 单据不漏通知

**Non-Goals:**

- 不改通知模板/优先级/extra_data 结构
- 不动盘点任务通知（branch 为 FK，本就精确；空分支随空分公司收敛一并受益）
- 不做通知偏好/免打扰体系

## Decisions

**1. 路由统一取 `_routing_branch(instance)`：业务分公司 FK 优先、文本快照兜底。**
一处口径（模型 property）供两端使用，消除「文本调出分公司」这个错误来源。实施中发现存量用例/历史单据可能只有文本分公司没有 FK（`业务分公司` 返回 None）——兜底按单据类型取对应文本（采购/归还=调入分公司文本，其余=调出分公司文本）再解析，兼容 ORM 直造单据。调拨的调入方驳回通知维持 `调入分公司`（该通道本就该通知调入方）。

**2. 空分公司分支：`branch is None` → 仅 `scope.all` 候选（admin 按入参照旧）。**
「范围覆盖未知分公司」的确定解释只有全量授权；宁可少发（全量授权者+admin 仍在）不可广播。数据异常（采购无调入方）本就不该发生，发生时也不放大。

**3. 状态识别改为成员判断 `in ('已通过', '已入库')`，驳回分支不变。**
审批动作语义=「单据生效」，两种状态文案只是类型差异。

**4. 创建人定位：`instance.created_by` 优先，`None` 时回退姓名匹配（存量单据 FK 可能为空）。**
自通知排除改为 `instance.created_by_id == approver.id` 优先、无 FK 时姓名比较兜底——与定位策略同构。

## Risks / Trade-offs

- [存量 branchless 单据/盘点任务的空分公司通知面收窄（全量→仅全量授权者）] → 该场景本属数据异常，收窄即纠偏
- [姓名回退仍可能重名错发（仅无 FK 的存量单据）] → 新单据全走 FK；存量随数据治理消化
- [采购审批通过后创建人将开始收到通知（原静默）] → 恢复本应有的行为，用户感知为修复而非噪音

## Migration Plan

纯代码，无迁移。部署即生效。上线验证：Web 端建采购单，仅调入分公司审批人（及全量授权者）收到待审批；审批通过后创建人收到结果通知。
