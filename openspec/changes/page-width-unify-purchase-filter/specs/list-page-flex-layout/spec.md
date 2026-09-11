# list-page-flex-layout 增量

## ADDED Requirements

### Requirement: 核心业务列表页版宽统一

核心业务列表页（资产流转各列表：采购入库/领用出库/调拨/回收单/回收台账；资产盘点页）的页面容器 SHALL 统一为 `max-width: 1600px; margin: 0 auto`——同屏并观一致，宽屏不拉伸到边（回收单基准）。各页 MUST NOT 再各自定义 1400px/100% 等异构宽度。

#### Scenario: 版宽一致

- **WHEN** 在 1920px 宽屏依次打开采购入库、领用出库、调拨、回收、盘点页
- **THEN** 各页内容区宽度一致（≤1600px 居中），无边到边拉伸页面
