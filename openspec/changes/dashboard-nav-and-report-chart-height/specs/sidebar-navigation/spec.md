# sidebar-navigation 增量

## ADDED Requirements

### Requirement: 工作台待审批入口与图表定高

工作台「待审批」统计卡片点击 MUST 跳转采购入库列表并自动套用「待审批」状态筛选（URL query 透传，列表页从 route.query 初始化状态）——MUST NOT 再经旧路由重定向到调拨。统计报表的图表卡片 SHALL 定高（内容超限内部滚动、标题常驻），页面总长 MUST NOT 随图表数据条数无限增长。

#### Scenario: 待审批直达

- **WHEN** 用户点击工作台「待审批」卡片
- **THEN** 进入采购入库列表且状态筛选为「待审批」，仅展示待审批采购单

#### Scenario: 图表定高滚动

- **WHEN** 分公司排行含 30+ 条数据渲染
- **THEN** 图表卡片高度恒定（≤480px），内容区内部滚动查看全部条目
