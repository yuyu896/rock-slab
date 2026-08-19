# transfer-list-action-buttons Specification

## Purpose
TBD - created by archiving change transfer-list-action-buttons. Update Purpose after archive.
## Requirements
### Requirement: 操作按钮有合适间距
流转 4 个列表页（采购入库/领用出库/调拨/回收）操作列的「详情/通过/驳回」按钮之间 SHALL 有合适间距，彼此不挤在一起。

#### Scenario: 按钮间有可见间距
- **WHEN** 任一流转列表页渲染一条含多个操作的单子
- **THEN** 相邻操作按钮之间有清晰的间距

#### Scenario: 隐藏按钮不影响间距
- **WHEN** 某按钮因审批状态（如非「待审批」）而隐藏
- **THEN** 剩余可见按钮之间仍保持合适间距

### Requirement: 操作按钮具备清晰按钮样式
操作按钮 SHALL 具备清晰的按钮样式并按操作区分状态色——详情中性、通过主色、驳回危险色，并具备 hover 反馈。

#### Scenario: 按钮呈可区分的按钮样式
- **WHEN** 查看流转列表的操作列
- **THEN** 详情/通过/驳回 呈现明显按钮样式且可按颜色区分（详情中性、通过主色、驳回危险色）

#### Scenario: hover 有反馈
- **WHEN** 鼠标悬停某操作按钮
- **THEN** 该按钮有明显 hover 反馈（如底色/边框变化）

