## 1. 实现

- [x] 1.1 `signals.py`：路由统一走 `_routing_branch(instance)`——业务分公司 FK 优先、文本快照兜底（实施中发现存量/ORM 直造单据只有文本，纯 FK 会掉通知）
- [x] 1.2 `_users_with_operation_access` 空分公司分支收敛为仅 admin+`scope.all`（docstring 同步「MUST NOT 广播」）
- [x] 1.3 pre_save 审批识别 `in ('已通过', '已入库')`；创建人定位 `_locate_creator`（created_by 优先、姓名回退）；自通知排除 `_is_recipient_self`（id 优先）

## 2. 测试

- [x] 2.1 新增 `tests/test_notification_routing.py` 4 例：Web 式采购不广播（无关分公司 0、调入方+全量授权者收到）；采购 approve（已入库）创建人收结果通知+抄送生成；重名不错收；驳回回归
- [x] 2.2 既有通知/岗位用例回归 + 全量 `pytest` 通过（906 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（Web 建采购单只通知调入方审批人；审批通过后创建人收到通知）

> 手验要点：以分公司A账号建采购单，仅 A 的审批人（及全量授权者）的待审批出现该单；B 司审批人无感；审批通过后创建人通知中心出现「审批通过」。
