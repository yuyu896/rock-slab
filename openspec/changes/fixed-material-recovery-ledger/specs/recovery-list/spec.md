## MODIFIED Requirements

### Requirement: Recovery sidebar entry

侧边栏资产流转分组下 SHALL 在“调拨”之后提供“回收”下拉菜单，菜单下包含“回收单”和“物资处置台账”两个入口。回收单入口导航到 `/transfers/recovery`，继续负责回收单创建、审批和查询；物资处置台账入口导航到 `/transfers/recovery/ledger`。原回收台账地址 MUST 保持可访问并展示物资处置台账。

#### Scenario: Sidebar shows recovery submenu

- **WHEN** 用户展开侧边栏“资产流转”分组并展开“回收”菜单
- **THEN** 显示“回收单”和“物资处置台账”两个子入口，分别导航到其对应页面

#### Scenario: Recovery document workflow remains available

- **WHEN** 用户点击“回收单”入口
- **THEN** 系统导航到 `/transfers/recovery`，用户继续使用原回收单创建、审批和查询流程

#### Scenario: Legacy ledger route remains compatible

- **WHEN** 用户访问已存在的 `/transfers/recovery/ledger` 地址或旧回收台账链接
- **THEN** 系统显示“物资处置台账”，不产生第二个独立台账入口
