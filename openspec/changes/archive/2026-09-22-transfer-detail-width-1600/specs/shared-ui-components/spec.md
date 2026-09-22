# shared-ui-components 增量

## ADDED Requirements

### Requirement: 单据详情页版宽 1600

单据详情共享布局（TransferDetailLayout）SHALL 以 `max-width: 1600px; margin: 0 auto` 呈现，与核心业务列表页版宽基准一致；响应式断点与移动端布局 MUST NOT 受影响。

#### Scenario: 宽屏下详情页铺满至 1600

- **WHEN** 视口宽度超过 1600px 时打开任一单据详情页
- **THEN** 内容区宽 1600px 居中，明细表列宽自适应摊开

#### Scenario: 窄屏响应式不变

- **WHEN** 视口宽度低于既有断点
- **THEN** 详情页按既有响应式规则呈现，与本变更前一致
