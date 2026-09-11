# inventory-item-basis 增量

## ADDED Requirements

### Requirement: 盘点库别退役回收库

盘点任务的库别（stock_bin）MUST 仅支持在库（stock）；携带/选择回收库（recycle）MUST 拒绝或不提供。存量回收库库别的历史任务数据保留（档案），其清单与报告不受影响。

#### Scenario: 创建盘点不可选回收库

- **WHEN** 用户在创建盘点任务页查看库别选项
- **THEN** 仅提供「在库」，无「回收库」选项；API 携带 stock_bin=recycle 返回 400
