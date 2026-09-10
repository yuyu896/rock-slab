# personnel-management 增量

## ADDED Requirements

### Requirement: 职级展示序——行政组长高于分公司行政

前端角色等级（ROLE_LEVELS）MUST 反映组织事实：admin > director > **leader（行政组长，管一个组）> manager（分公司行政，管单家分公司）** > 退役岗位。组织架构等按职级排序的人员列表 MUST 将行政组长排在分公司行政之前。等级 MUST NOT 驱动任何权限/数据范围/审批判断（那些按授权码与任命展开，既有口径不变）。

#### Scenario: 组织架构人员排序

- **WHEN** 同一节点下并列展示行政组长与分公司行政
- **THEN** 行政组长排在分公司行政之前，同职级按姓名
